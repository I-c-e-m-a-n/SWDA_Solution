"""Official SDK protocol/transport with pre-dispatch governance middleware."""

import argparse
import logging
import sys
import time
from contextvars import ContextVar
from threading import BoundedSemaphore
from uuid import uuid4

import anyio
from mcp import MCPError
from mcp.server import MCPServer
from mcp.server.caching import CacheHint
from mcp.server.context import CallNext, ServerRequestContext
from mcp.types import CallToolResult
from pydantic import ValidationError

from . import AGENT_VERSION, PROTOCOL_VERSION, PUBLIC_TOOL, audit
from .agent import recommend
from .artefacts import schema_digest
from .policy import Policy, SafeFailure
from .schemas import RecommendationRequest, RecommendationResponse

trace_context = ContextVar("trace_id", default="")
ERROR_CODES = {
    "validation": -32602,
    "policy_denial": -32001,
    "dependency_failure": -32002,
    "internal_failure": -32603,
    "unsupported_protocol": -32003,
}


class Governance:
    def __init__(self, policy: Policy):
        self.policy = policy
        self.server = None
        self.limiter = anyio.CapacityLimiter(4)
        self.worker_slots = BoundedSemaphore(4)

    def run_worker(self, function):
        # Abandoned threads retain this physical work slot until they really finish.
        if not self.worker_slots.acquire(blocking=False):
            raise SafeFailure("dependency_failure")
        try:
            return function()
        finally:
            self.worker_slots.release()

    async def __call__(self, ctx: ServerRequestContext, call_next: CallNext):
        trace = uuid4().hex
        token = trace_context.set(trace)
        started = time.monotonic()
        revision = None
        status = "allowed"
        try:
            with anyio.fail_after(3):
                if ctx.protocol_version != PROTOCOL_VERSION or ctx.method == "initialize":
                    raise SafeFailure("unsupported_protocol")
                if ctx.method in {"server/discover", "tools/list", "tools/call"}:
                    tools = await self.server.list_tools()
                    tool = PUBLIC_TOOL
                    if ctx.method == "tools/call":
                        raw = dict(ctx.params or {})
                        tool = raw.get("name")
                        if tool != PUBLIC_TOOL:
                            raise SafeFailure("policy_denial")
                        args = raw.get("arguments")
                        if not isinstance(args, dict) or set(args) != {"request"}:
                            raise SafeFailure("validation")
                        RecommendationRequest.model_validate(args["request"])
                    approval = await anyio.to_thread.run_sync(
                        self.run_worker,
                        lambda: self.policy.authorize(tool, schema_digest(tools)),
                        abandon_on_cancel=True,
                        limiter=self.limiter,
                    )
                    revision = approval.policy_revision
                result = await call_next(ctx)
                if ctx.method == "tools/call":
                    result = CallToolResult.model_validate(result)
                    # SDK tools can turn exceptions into isError. Never forward their raw text.
                    if getattr(result, "is_error", False):
                        raise SafeFailure("internal_failure")
                    try:
                        RecommendationResponse.model_validate(result.structured_content)
                    except ValidationError:
                        raise SafeFailure("internal_failure") from None
                    if len(result.model_dump_json().encode()) > 16384:
                        raise SafeFailure("internal_failure")
                return result
        except (ValidationError, TypeError):
            status = "validation"
            raise MCPError(
                code=ERROR_CODES[status],
                message=status,
                data={"trace_id": trace, "category": status},
            ) from None
        except Exception as exc:
            status = exc.category if isinstance(exc, SafeFailure) else "internal_failure"
            if isinstance(exc, MCPError) and exc.message in ERROR_CODES:
                status = exc.message
            if isinstance(exc, TimeoutError):
                status = "dependency_failure"
            raise MCPError(
                code=ERROR_CODES[status],
                message=status,
                data={"trace_id": trace, "category": status},
            ) from None
        finally:
            operation = (
                ctx.method
                if ctx.method in {"tools/list", "tools/call", "server/discover", "initialize"}
                else "other"
            )
            audit.event(trace, status, (time.monotonic() - started) * 1000, revision, operation)
            trace_context.reset(token)


def build_server(policy: Policy | None = None) -> MCPServer:
    governance = Governance(policy or Policy())
    server = MCPServer(
        "SWDA synthetic recommendation",
        version=AGENT_VERSION,
        middleware=[governance],
        subscriptions=False,
        cache_hints={"tools/list": CacheHint(), "server/discover": CacheHint()},
        instructions="Synthetic advisory demonstration; no official eligibility decisions.",
    )
    governance.server = server

    @server.tool()
    async def recommend_service(request: RecommendationRequest) -> RecommendationResponse:
        """Recommend invented programmes from a read-only synthetic catalogue."""
        try:
            response = await anyio.to_thread.run_sync(
                governance.run_worker,
                lambda: recommend(request, trace_context.get()),
                abandon_on_cancel=True,
                limiter=governance.limiter,
            )
            # Validate before SDK conversion so unexpected output never reaches SDK crash logs.
            return RecommendationResponse.model_validate(response)
        except SafeFailure as exc:
            raise MCPError(code=ERROR_CODES[exc.category], message=exc.category) from None
        except Exception:
            raise MCPError(
                code=ERROR_CODES["internal_failure"], message="internal_failure"
            ) from None

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    # No SDK exception/debug/request logs: our safe JSON events go only to stderr.
    logging.basicConfig(stream=sys.stderr, level=logging.CRITICAL, format="%(message)s")
    logging.getLogger("swda.audit").setLevel(logging.INFO)
    server = build_server()
    if args.transport == "stdio":
        server.run()
    else:
        if not 1024 <= args.port <= 65535:
            parser.error("port must be between 1024 and 65535")
        server.run(
            "streamable-http",
            host="127.0.0.1",
            port=args.port,
            stateless_http=True,
            json_response=True,
            max_request_body_size=16384,
        )


if __name__ == "__main__":
    main()
