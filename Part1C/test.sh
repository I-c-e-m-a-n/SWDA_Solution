#!/bin/bash
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x .venv/bin/python ]; then
    echo 'Run ./setup.sh first.' >&2
    exit 1
fi
export PYTHONPATH="$PWD/src"
.venv/bin/python -m ruff format --check src tests
.venv/bin/python -m ruff check src tests
exec .venv/bin/python -m pytest "$@"
