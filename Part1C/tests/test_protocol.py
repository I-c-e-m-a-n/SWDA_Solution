"""Real SDK clients over subprocess stdio and loopback HTTP, plus injected failures."""

import http.client
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time

import pytest
from mcp import Client, MCPError, StdioServerParameters
from mcp.types import DiscoverResult

from swda_part1c import PROTOCOL_VERSION, PUBLIC_TOOL
from swda_part1c.artefacts import ROOT
from swda_part1c.client_demo import DEMO_REQUEST, stdio_params
from swda_part1c.schemas import RecommendationResponse
from swda_part1c.server import build_server

pytestmark = pytest.mark.anyio


async def probe(client):
    raw = await client.session.send_discover(PROTOCOL_VERSION)
    discovery = DiscoverResult.model_validate(raw)
    assert PROTOCOL_VERSION in discovery.supported_versions
    assert discovery.ttl_ms == 0
    assert discovery.cache_scope == "private"
    assert client.protocol_version == PROTOCOL_VERSION
    tools = await client.list_tools(cache_mode="refresh")
    assert [tool.name for tool in tools.tools] == [PUBLIC_TOOL]
    assert tools.ttl_ms == 0
    assert (
        tools.tools[0].input_schema["$defs"]["RecommendationRequest"]["additionalProperties"]
        is False
    )
    result = await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
    assert not result.is_error
    parsed = RecommendationResponse.model_validate(result.structured_content)
    assert parsed.status == "recommended"
    assert [p.programme_id for p in parsed.recommendations] == ["SYN-E01", "SYN-E02"]
    assert result.content


async def test_subprocess_stdio():
    async with Client(stdio_params(), mode=PROTOCOL_VERSION, read_timeout_seconds=10) as client:
        await probe(client)
        with pytest.raises(MCPError):
            await client.session.send_discover("2099-01-01")


async def test_auto_discovery_modern():
    # auto MUST really probe, and the server forbids legacy initialize fallback.
    async with Client(stdio_params(), read_timeout_seconds=10) as client:
        assert client.protocol_version == PROTOCOL_VERSION
        assert client.session.discover_result is not None


@pytest.fixture
def http_server(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    log = (tmp_path / "server.log").open("w+", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "swda_part1c.server",
            "--transport",
            "streamable-http",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=log,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                log.seek(0)
                pytest.fail(log.read())
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("HTTP startup timeout")
        yield port
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()


async def test_loopback_http(http_server):
    async with Client(
        f"http://127.0.0.1:{http_server}/mcp", mode=PROTOCOL_VERSION, read_timeout_seconds=10
    ) as client:
        await probe(client)


def post(port, *, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(
            "POST",
            "/mcp",
            body=body
            or json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "server/discover",
                    "params": {
                        "_meta": {
                            "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
                            "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
                            "io.modelcontextprotocol/clientCapabilities": {},
                        }
                    },
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": PROTOCOL_VERSION,
                "Mcp-Method": "server/discover",
                **(headers or {}),
            },
        )
        response = conn.getresponse()
        return response.status, response.read()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Host": "evil.example"},
        {"MCP-Protocol-Version": "2099-01-01"},
        {"Mcp-Method": "tools/list"},
    ],
)
async def test_http_host_origin_protocol_protection(http_server, headers):
    baseline_status, baseline = post(http_server)
    assert baseline_status == 200 and b'"supportedVersions"' in baseline
    status, body = post(http_server, headers=headers)
    assert status >= 400 or b'"error"' in body


async def test_http_body_bound(http_server):
    status, _ = post(http_server, body=" " * 16385)
    assert status == 413


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"request": {}},
        {
            "request": {
                "request_id": "r",
                "request_text": "job",
                "channel": "web",
                "identity": "admin",
            }
        },
        {"request": {"request_id": "r", "request_text": "x" * 2001, "channel": "web"}},
        {"request": {"request_id": "r", "request_text": "job", "channel": "web"}, "extra": 1},
    ],
)
async def test_protocol_contract_errors(policy, args, monkeypatch):
    import swda_part1c.server as module

    def never(*_):
        pytest.fail("Invalid request reached internal engine")

    monkeypatch.setattr(module, "recommend", never)
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="validation") as exc:
            await client.call_tool(PUBLIC_TOOL, args)
        assert "request_text" not in str(exc.value)


@pytest.mark.parametrize("name", ["classify", "lookup", "shell", "approve_agent"])
async def test_unknown_tools(policy, name):
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError):
            await client.call_tool(name, {})


@pytest.mark.parametrize("state", ["REVOKED", "SUSPENDED", "APPROVED"])
async def test_cached_discovery_does_not_authorize(policy, policy_path, policy_record, state):
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        await probe(client)
        policy_record["state"] = state
        policy_record["policy_revision"] = 2
        policy_path.write_text(json.dumps(policy_record), encoding="utf-8")
        with pytest.raises(MCPError, match="policy_denial"):
            await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
        with pytest.raises(MCPError, match="policy_denial"):
            await client.list_tools(cache_mode="refresh")
        with pytest.raises(MCPError, match="policy_denial"):
            await client.session.send_discover(PROTOCOL_VERSION)


async def test_policy_disappearance_after_discovery(policy, policy_path):
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        await probe(client)
        policy_path.unlink()
        with pytest.raises(MCPError, match="dependency_failure"):
            await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)


async def test_dependency_error_and_private_logs(policy, monkeypatch, caplog):
    import swda_part1c.agent as module

    def broken(*_):
        raise OSError("SECRET-XYZ /private/person.txt")

    monkeypatch.setattr(module, "lookup", broken)
    caplog.set_level(logging.INFO, logger="swda.audit")
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="dependency_failure") as exc:
            await client.call_tool(
                PUBLIC_TOOL,
                {
                    "request": {
                        "request_id": "r",
                        "request_text": "SECRET-XYZ job",
                        "channel": "web",
                    }
                },
            )
        assert "SECRET-XYZ" not in str(exc.value)
        assert "SECRET-XYZ" not in caplog.text
        assert "/private/person" not in caplog.text
        events = [json.loads(r.message) for r in caplog.records if r.name == "swda.audit"]
        assert events[-1]["status"] == "dependency_failure"
        assert events[-1]["trace_id"] == exc.value.data["trace_id"]


async def test_internal_error_sanitized(policy, monkeypatch):
    import swda_part1c.server as module

    def broken(*_):
        raise RuntimeError("SECRET-XYZ")

    monkeypatch.setattr(module, "recommend", broken)
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="internal_failure") as exc:
            await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
        assert "SECRET-XYZ" not in str(exc.value)


async def test_execution_deadline(policy, monkeypatch):
    import swda_part1c.server as module

    original = module.recommend

    def delayed(*args):
        time.sleep(3.2)
        return original(*args)

    monkeypatch.setattr(module, "recommend", delayed)
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="dependency_failure"):
            await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)


async def test_demo_in_path_with_spaces(tmp_path):
    target = tmp_path / "repo with spaces" / "Part1C"
    shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".*cache"))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "swda_part1c.server"],
        cwd=str(target),
        env={"PYTHONPATH": str(target / "src")},
    )
    async with Client(params, mode=PROTOCOL_VERSION, read_timeout_seconds=10) as client:
        await probe(client)
    # Exercise the actual Bash launcher too, from an unrelated working directory.
    (target / ".venv").symlink_to(ROOT / ".venv", target_is_directory=True)
    run = subprocess.run(
        [str(target / "demo.sh")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert json.loads(run.stdout)["observed_protocol"] == PROTOCOL_VERSION
    assert "request_text" not in run.stderr
    assert "I need help finding a job" not in run.stderr


async def test_legacy_not_required_or_accepted():
    with pytest.RaisesGroup(MCPError, flatten_subgroups=True, allow_unwrapped=True):
        async with Client(stdio_params(), mode="legacy", read_timeout_seconds=5):
            pytest.fail("Legacy handshake unexpectedly accepted")


async def test_success_audit_metadata(policy, caplog):
    caplog.set_level(logging.INFO, logger="swda.audit")
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        result = await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
    events = [json.loads(r.message) for r in caplog.records if r.name == "swda.audit"]
    events = [e for e in events if e["operation"] == "tools/call"]
    assert events[-1]["trace_id"] == result.structured_content["trace_id"]
    assert events[-1]["policy_revision"] == 1
    assert events[-1]["status"] == "allowed"
    assert "request_text" not in caplog.text


async def test_subprocess_revocation(policy_path, policy_record):
    # Inject an operator-owned temporary fixture, never a client-supplied policy path.
    code = (
        "from pathlib import Path; from swda_part1c.server import build_server; "
        "from swda_part1c.policy import Policy; "
        f"build_server(Policy(Path({str(policy_path)!r}))).run()"
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", code],
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    async with Client(params, mode=PROTOCOL_VERSION, read_timeout_seconds=10) as client:
        await probe(client)
        policy_record["state"] = "REVOKED"
        policy_path.write_text(json.dumps(policy_record), encoding="utf-8")
        for _ in range(3):
            with pytest.raises(MCPError, match="policy_denial"):
                await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
        with pytest.raises(MCPError, match="policy_denial"):
            await client.list_tools(cache_mode="refresh")


async def test_unexpected_registered_tool_fails_closed(policy):
    server = build_server(policy)

    @server.tool()
    def accidental_tool() -> str:
        return "should never be exposed"

    async with Client(server, mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="policy_denial"):
            await client.list_tools()


async def test_invalid_output_is_internal_failure(policy, monkeypatch):
    import swda_part1c.server as module

    monkeypatch.setattr(module, "recommend", lambda *_: {"invalid": "SECRET-XYZ"})
    async with Client(build_server(policy), mode=PROTOCOL_VERSION) as client:
        with pytest.raises(MCPError, match="internal_failure") as exc:
            await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
        assert "SECRET-XYZ" not in str(exc.value)


async def test_physical_worker_limit(policy):
    from swda_part1c.server import Governance

    governance = Governance(policy)
    for _ in range(4):
        assert governance.worker_slots.acquire(blocking=False)
    from swda_part1c.policy import SafeFailure

    with pytest.raises(SafeFailure, match="dependency_failure"):
        governance.run_worker(lambda: pytest.fail("No worker capacity"))
    for _ in range(4):
        governance.worker_slots.release()
    assert governance.run_worker(lambda: "recovered") == "recovered"
