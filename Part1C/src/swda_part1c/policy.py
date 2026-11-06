"""Fresh bounded fixture reads, exact release binding, no positive decision cache."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from . import AGENT_ID, AGENT_VERSION, INTERNAL_TOOLS, PUBLIC_TOOL
from .artefacts import ROOT, digest, read_json
from .registry import State
from .schemas import StrictModel


class SafeFailure(Exception):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


class Approval(StrictModel):
    simulation: Literal[True]
    agent_id: str
    agent_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    artefact_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    schema_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    tools: Annotated[list[str], Field(min_length=1, max_length=1)]
    internal_tools: Annotated[list[str], Field(min_length=2, max_length=2)]
    approved_clients: Annotated[list[str], Field(min_length=1, max_length=10)]
    service_scope: str
    environment: str
    state: State
    expires_at: AwareDatetime
    policy_revision: Annotated[int, Field(ge=1)]
    developer: str
    security_reviewer: str
    business_approver: str
    publisher: str
    evidence: str


class Policy:
    def __init__(
        self,
        path: Path = ROOT / "policy/approved_agent.json",
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        digest_provider: Callable[[], str] = digest,
        client_scope: str = "trusted-local-host",
        environment: str = "local-demo",
        service_scope: str = "synthetic-recommendations",
    ):
        # Operator-owned configuration, never derived from client headers/arguments.
        self.path = path
        self.clock = clock
        self.digest_provider = digest_provider
        self.client_scope = client_scope
        self.environment = environment
        self.service_scope = service_scope

    def authorize(self, tool: str, schemas: str) -> Approval:
        try:
            # Bounded file reading; JSON validation preserves datetime/enum JSON semantics.
            record = Approval.model_validate_json(json.dumps(read_json(self.path)))
        except Exception:
            raise SafeFailure("dependency_failure") from None
        try:
            actual_digest = self.digest_provider()
        except Exception:
            raise SafeFailure("dependency_failure") from None
        if not (
            record.agent_id == AGENT_ID
            and record.agent_version == AGENT_VERSION
            and record.artefact_digest == actual_digest
            and record.schema_digest == schemas
            and tool == PUBLIC_TOOL
            and record.tools == [PUBLIC_TOOL]
            and record.internal_tools == list(INTERNAL_TOOLS)
            and record.approved_clients == [self.client_scope]
            and record.environment == self.environment
            and record.service_scope == self.service_scope
            and record.state == State.PUBLISHED
            and record.expires_at > self.clock()
            and len(
                {
                    record.developer,
                    record.security_reviewer,
                    record.business_approver,
                    record.publisher,
                }
            )
            == 4
        ):
            raise SafeFailure("policy_denial")
        return record
