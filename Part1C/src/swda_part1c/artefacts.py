"""Deterministic release digest and bounded read helpers; no caller-controlled paths."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path, limit: int = 65536):
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Artefact too large")
    return json.loads(raw)


def digest(root: Path = ROOT) -> str:
    # Path + NUL + length + NUL + bytes; sort POSIX paths. Policy excluded.
    paths = sorted(
        [
            *root.glob("src/swda_part1c/*.py"),
            root / "data/synthetic_programmes.json",
            root / "pyproject.toml",
            root / "requirements.lock",
        ],
        key=lambda p: p.relative_to(root).as_posix(),
    )
    h = hashlib.sha256()
    for path in paths:
        if path.is_symlink():
            raise ValueError("Symlink artefact forbidden")
        with path.open("rb") as stream:
            data = stream.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Artefact too large")
        h.update(path.relative_to(root).as_posix().encode() + b"\0")
        h.update(str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()


def schema_digest(tools) -> str:
    schemas = {t.name: {"input": t.input_schema, "output": t.output_schema} for t in tools}
    return hashlib.sha256(
        json.dumps(schemas, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
