#!/usr/bin/env bash
set -euo pipefail
PART="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="${SWDA_VENV:-$PART/.venv}"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$PART/requirements.lock"
"$VENV/bin/python" -m pip install --disable-pip-version-check --no-build-isolation --no-deps -e "$PART"
mkdir -p "$PART/runtime"
cd "$PART"
"$VENV/bin/python" -m pytest -q --junitxml="$PART/runtime/pytest.xml"
"$VENV/bin/python" -m swda_part2c.cli demo
