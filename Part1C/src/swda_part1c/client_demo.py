"""Real SDK client; pins modern mode, then explicitly performs server/discover."""

import argparse
import asyncio
import json
import sys

from mcp import Client, StdioServerParameters
from mcp.types import DiscoverResult

from . import PROTOCOL_VERSION, PUBLIC_TOOL
from .artefacts import ROOT
from .schemas import RecommendationResponse

DEMO_REQUEST = {
    "request": {
        "request_id": "demo-001",
        "request_text": "I need help finding a job.",
        "channel": "web",
    }
}


def stdio_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "swda_part1c.server"],
        cwd=str(ROOT),
        env={"PYTHONPATH": str(ROOT / "src")},
    )


async def demo(url: str | None = None):
    if url is not None and url != "http://127.0.0.1:8765/mcp":
        raise ValueError("Demo accepts only the documented loopback URL")
    async with Client(
        url or stdio_params(), mode=PROTOCOL_VERSION, read_timeout_seconds=10, cache=None
    ) as client:
        # Pinning Client synthesizes capabilities; send_discover forces a real wire probe.
        discovery = DiscoverResult.model_validate(
            await client.session.send_discover(PROTOCOL_VERSION)
        )
        assert PROTOCOL_VERSION in discovery.supported_versions
        assert client.protocol_version == PROTOCOL_VERSION
        tools = await client.list_tools()
        assert [t.name for t in tools.tools] == [PUBLIC_TOOL]
        result = await client.call_tool(PUBLIC_TOOL, DEMO_REQUEST)
        assert not result.is_error
        response = RecommendationResponse.model_validate(result.structured_content)
        print(
            json.dumps(
                {
                    "observed_protocol": client.protocol_version,
                    "discovered_tools": [t.name for t in tools.tools],
                    "response": response.model_dump(),
                },
                indent=2,
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url")
    args = parser.parse_args()
    asyncio.run(demo(args.url))


if __name__ == "__main__":
    main()
