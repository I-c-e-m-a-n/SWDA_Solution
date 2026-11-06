#!/bin/bash
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x .venv/bin/python ]; then
    echo 'Run ./setup.sh first.' >&2
    exit 1
fi
export PYTHONPATH="$PWD/src"
exec .venv/bin/python -m swda_part1c.client_demo "$@"
