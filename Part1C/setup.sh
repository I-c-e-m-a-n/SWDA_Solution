#!/bin/bash
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN=${PYTHON_BIN:-python3.12}
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo 'Python 3.12 is required. Install the macOS universal2 Python 3.12 installer from https://www.python.org/downloads/macos/ (Apple Silicon or Intel), then rerun. No sudo or system Python changes are needed.' >&2
    exit 1
fi
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Python 3.12 required; use PYTHON_BIN=/path/to/python3.12")'
if [ ! -d .venv ]; then
    "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Existing .venv is not Python 3.12; move it aside and rerun setup.")'
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
.venv/bin/python -m pip check
PYTHONPATH="$PWD/src" .venv/bin/python -c 'from mcp import Client; from mcp.server import MCPServer; from swda_part1c.server import build_server; build_server(); print("MCP v2 imports OK")'
