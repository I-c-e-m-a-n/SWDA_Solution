import hashlib
from pathlib import Path
from types import MappingProxyType
from .schemas import Annex, Source
from .release import EXPECTED, TEST_EXPECTED, MANIFEST_VERSION

ROOT = Path(__file__).resolve().parents[2]

class SourceIntegrityError(ValueError):
    pass

class Catalogue:
    def __init__(self, path: Path | None = None):
        path = path or ROOT / 'data/annex-v1.json'
        try:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != (EXPECTED | TEST_EXPECTED)[path.name]:
                raise SourceIntegrityError('SOURCE_DIGEST_MISMATCH')
            annex = Annex.model_validate_json(raw)
            expected_ids = {f'MO-{i:02}' for i in range(1, 9)} | {f'S{i}' for i in range(1, 6)}
            records = {r.source_id: r for r in annex.records}
            if set(records) != expected_ids or len(records) != 13 or annex.version != 'annex-1':
                raise SourceIntegrityError('SOURCE_SCOPE_VERSION')
            if any(r.version != annex.version for r in annex.records):
                raise SourceIntegrityError('SOURCE_RECORD_VERSION')
            self._records = MappingProxyType(records)
            self.manifest = MappingProxyType(dict({path.name:(EXPECTED | TEST_EXPECTED)[path.name]}, manifest_version=MANIFEST_VERSION))
            self.version = annex.version
        except (OSError, KeyError, ValueError) as exc:
            raise SourceIntegrityError(str(exc)) from exc

    def read(self, ids: tuple[str, ...]) -> tuple[Source, ...]:
        if not set(ids) <= self._records.keys():
            raise SourceIntegrityError('UNKNOWN_SOURCE')
        return tuple(self._records[i] for i in ids)
