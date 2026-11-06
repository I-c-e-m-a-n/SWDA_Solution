"""Offline lifecycle simulation, deliberately not exposed as an MCP tool."""

from enum import StrEnum


class State(StrEnum):
    DRAFT = "DRAFT"
    REGISTERED = "REGISTERED"
    VALIDATED = "VALIDATED"
    SECURITY_REVIEWED = "SECURITY_REVIEWED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    REAPPROVAL_REQUIRED = "REAPPROVAL_REQUIRED"


TRANSITIONS = {
    (State.DRAFT, State.REGISTERED): "developer",
    (State.REGISTERED, State.VALIDATED): "validator",
    (State.REGISTERED, State.REJECTED): "validator",
    (State.VALIDATED, State.SECURITY_REVIEWED): "security",
    (State.VALIDATED, State.REJECTED): "security",
    (State.SECURITY_REVIEWED, State.APPROVED): "business",
    (State.SECURITY_REVIEWED, State.REJECTED): "business",
    (State.APPROVED, State.PUBLISHED): "publisher",
    (State.APPROVED, State.REAPPROVAL_REQUIRED): "publisher",
    (State.PUBLISHED, State.SUSPENDED): "security",
    (State.PUBLISHED, State.REVOKED): "security",
    (State.PUBLISHED, State.REAPPROVAL_REQUIRED): "security",
    (State.SUSPENDED, State.REVOKED): "security",
    (State.SUSPENDED, State.REAPPROVAL_REQUIRED): "security",
    (State.REAPPROVAL_REQUIRED, State.DRAFT): "developer",
}


def transition(
    current: State,
    target: State,
    *,
    role: str,
    actor: str,
    developer: str,
    new_version: bool = False,
) -> State:
    if TRANSITIONS.get((current, target)) != role:
        raise ValueError("Invalid transition or authority")
    if role != "developer" and actor == developer:
        raise ValueError("Independent authority required")
    if (current, target) == (State.REAPPROVAL_REQUIRED, State.DRAFT) and not new_version:
        raise ValueError("New immutable version required")
    return target
