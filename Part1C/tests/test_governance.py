import asyncio
import json
import shutil
from datetime import UTC, datetime

import pytest

from swda_part1c import PUBLIC_TOOL
from swda_part1c.artefacts import ROOT, digest, schema_digest
from swda_part1c.policy import SafeFailure
from swda_part1c.registry import TRANSITIONS, State, transition
from swda_part1c.server import build_server


def schemas():
    return schema_digest(asyncio.run(build_server().list_tools()))


def test_published(policy):
    record = policy.authorize(PUBLIC_TOOL, schemas())
    assert record.state == State.PUBLISHED


@pytest.mark.parametrize(
    ("field", "value"),
    [("state", state.value) for state in State if state != State.PUBLISHED]
    + [
        ("agent_version", "9.0.0"),
        ("agent_id", "other"),
        ("artefact_digest", "0" * 64),
        ("schema_digest", "0" * 64),
        ("tools", ["shell"]),
        ("internal_tools", ["classify", "shell"]),
        ("approved_clients", ["untrusted"]),
        ("service_scope", "production"),
        ("environment", "production"),
        ("expires_at", "2026-11-06T00:00:00Z"),
        ("policy_revision", 0),
        ("business_approver", "synthetic-developer"),
    ],
)
def test_policy_negatives(policy, policy_path, policy_record, field, value):
    policy_record[field] = value
    policy_path.write_text(json.dumps(policy_record), encoding="utf-8")
    with pytest.raises(SafeFailure):
        policy.authorize(PUBLIC_TOOL, schemas())


@pytest.mark.parametrize("kind", ["missing", "directory", "corrupt", "oversize"])
def test_outage(policy, policy_path, kind):
    if kind == "missing":
        policy_path.unlink()
    elif kind == "directory":
        policy_path.unlink()
        policy_path.mkdir()
    else:
        policy_path.write_text("!" if kind == "corrupt" else " " * 65537, encoding="utf-8")
    with pytest.raises(SafeFailure, match="dependency_failure"):
        policy.authorize(PUBLIC_TOOL, schemas())


def test_digest_failure(policy):
    def broken():
        raise OSError("SECRET-XYZ")

    policy.digest_provider = broken
    with pytest.raises(SafeFailure, match="dependency_failure"):
        policy.authorize(PUBLIC_TOOL, schemas())


def test_undeclared_tool_and_clock(policy):
    with pytest.raises(SafeFailure):
        policy.authorize("lookup", schemas())
    policy.clock = lambda: datetime(2028, 1, 1, tzinfo=UTC)
    with pytest.raises(SafeFailure):
        policy.authorize(PUBLIC_TOOL, schemas())


def test_digest_collection(tmp_path):
    copy = tmp_path / "path with spaces"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".*cache"))
    assert digest(copy) == digest()
    (copy / "policy/approved_agent.json").write_text("changed", encoding="utf-8")
    assert digest(copy) == digest()
    (copy / "src/swda_part1c/classifier.py").write_text("changed", encoding="utf-8")
    assert digest(copy) != digest()


@pytest.mark.parametrize(("edge", "role"), list(TRANSITIONS.items()))
def test_transitions(edge, role):
    assert (
        transition(*edge, role=role, actor="independent", developer="dev", new_version=True)
        == edge[1]
    )


@pytest.mark.parametrize("current", list(State))
def test_invalid_transition(current):
    with pytest.raises(ValueError):
        transition(current, current, role="developer", actor="dev", developer="dev")


def test_separation_of_duties():
    with pytest.raises(ValueError):
        transition(
            State.SECURITY_REVIEWED, State.APPROVED, role="business", actor="dev", developer="dev"
        )
    with pytest.raises(ValueError):
        transition(State.APPROVED, State.PUBLISHED, role="developer", actor="dev", developer="dev")
    with pytest.raises(ValueError):
        transition(
            State.REAPPROVAL_REQUIRED, State.DRAFT, role="developer", actor="dev", developer="dev"
        )
