import json
from datetime import UTC, datetime

import pytest

from swda_part1c.artefacts import ROOT
from swda_part1c.policy import Policy


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def request_data():
    return {"request_id": "test-001", "request_text": "I need a job", "channel": "web"}


@pytest.fixture
def policy_record():
    return json.loads((ROOT / "policy/approved_agent.json").read_text(encoding="utf-8"))


@pytest.fixture
def policy_path(tmp_path, policy_record):
    path = tmp_path / "approval.json"
    path.write_text(json.dumps(policy_record), encoding="utf-8")
    return path


@pytest.fixture
def policy(policy_path):
    return Policy(policy_path, clock=lambda: datetime(2026, 11, 6, tzinfo=UTC))
