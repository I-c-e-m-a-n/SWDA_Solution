"""Immutable strict contracts; model output never supplies trusted identity."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Actor = Literal['TA', 'PA', 'EA', 'REV']
Role = Literal['TA', 'PA', 'EA']
RunType = Literal['CANDIDATE', 'CF', 'TEST']
Classification = Literal['KNOWN', 'VARIATION', 'NEW', 'INCONCLUSIVE']
Status = Literal['RUNNING', 'COMPLETE', 'BLOCKED', 'INCOMPLETE', 'NO_PATTERN',
                 'REVIEW_PENDING', 'APPROVED_FOR_INVESTIGATION', 'REJECTED', 'REVISION_REQUESTED']
Action = Literal['APPROVE_FOR_INVESTIGATION', 'REJECT', 'REQUEST_REVISION']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)

class Limits(Strict):
    cards: int = Field(default=3, ge=1, le=3)
    cf: int = Field(default=3, ge=0, le=3)
    rounds: int = Field(default=4, ge=1, le=4)
    turns: int = Field(default=12, ge=1, le=12)
    retries: int = Field(default=2, ge=0, le=2)
    seconds: float = Field(default=120.0, gt=0, le=120)
    lineage_calls: int = Field(default=48, ge=1, le=48)
    test_fixtures: int = Field(default=12, ge=1, le=12)
    test_calls: int = Field(default=12, ge=1, le=12)
    suite_calls: int = Field(default=60, ge=1, le=60)

class Profile(Strict):
    actor: Actor
    incentive: str
    capabilities: tuple[Literal['propose', 'reply', 'reference_lookup', 'review'], ...]
    sources: tuple[str, ...]
    recipients: tuple[str, ...]
    prohibited: tuple[str, ...] = ('approve', 'write', 'shell', 'network', 'peer_call')

class Scenario(Strict):
    scenario_id: str
    version: str = '1'
    fixture_version: str = 'scripts-2'
    source_version: str = 'annex-1'
    policy_version: str = 'acl-1'
    seed: int = 17
    roles: tuple[Role, ...]
    sources: tuple[str, ...]
    features: tuple[str, ...]
    mode: Literal['dependency', 'single', 'benign', 'insufficient']
    rounds: int = Field(default=2, ge=1, le=4)
    fault: str = ''

    @model_validator(mode='after')
    def unique_inputs(self):
        if not self.roles or not self.sources or any(len(v) != len(set(v)) for v in
                (self.roles, self.sources, self.features)):
            raise ValueError('SCENARIO_EMPTY_OR_DUPLICATE_INPUTS')
        return self

class Source(Strict):
    source_id: str
    version: str
    source_type: Literal['ANNEX_A', 'ANNEX_B']
    name: str
    text: str
    basis: str
    trust: Literal['ILLUSTRATIVE', 'EXERCISE_UNVERIFIED']
    benign: bool = False

class Annex(Strict):
    version: str
    records: tuple[Source, ...]

class Claim(Strict):
    label: Literal['SOURCE', 'SIMULATION', 'ASSUMPTION']
    text: str = Field(min_length=5, max_length=1000)
    source_ids: tuple[str, ...]
    @model_validator(mode='after')
    def attributed(self):
        if not self.source_ids:
            raise ValueError('Every assertion requires attributable source context')
        return self

class Contribution(Strict):
    actor: Role
    claim: Claim
    benefit: Claim
    features: tuple[str, ...]
    depends_on: tuple[str, ...]
    dependency_features: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    material: bool

class Envelope(Strict):
    schema_version: Literal['2'] = '2'
    run_id: str
    run_type: RunType
    message_id: str
    parent_message_id: str | None
    actor: Actor
    recipient: str
    purpose: Literal['propose', 'reply', 'review', 'reference_lookup']
    source_ids: tuple[str, ...]
    policy_version: str
    source_version: str
    round: int = Field(ge=1, le=4)
    turn: int = Field(ge=1, le=12)
    attempt: int = Field(ge=0, le=2)

class Response(Strict):
    operation: Literal['propose', 'reply']
    recipient: str
    claims: tuple[Claim, ...]
    contribution: Contribution

class Message(Strict):
    envelope: Envelope
    response: Response

class Lookup(Strict):
    actor: Literal['REV'] = 'REV'
    purpose: Literal['mo_comparison', 'provenance_check']
    source_ids: tuple[str, ...]

class Context(Strict):
    envelope: Envelope
    profile: Profile
    scenario: Scenario
    references: tuple[Source, ...]
    incoming: tuple[Message, ...]
    prior: tuple[Message, ...]
    draft: dict | None = None
    comparison: dict | None = None

class PolicyDecision(Strict):
    allowed: bool
    stage: str
    code: str
    message_id: str

class Counterfactual(Strict):
    run_id: str
    parent_run_id: str
    removed_actor: Role
    outcome: Literal['MULTI_PARTY_DEPENDENCY', 'SURVIVING_COALITION', 'SINGLE_ACTOR_FEASIBILITY', 'INCONCLUSIVE']
    surviving_actors: tuple[Role, ...]
    excluded_parent_messages: tuple[str, ...]
    rationale: str

class Recommendation(Strict):
    classification: Classification
    matches: tuple[str, ...]
    rationale: str
    evidence_strength: Literal['weak_unverified'] = 'weak_unverified'
    limitations: tuple[str, ...]
    missing_data: tuple[str, ...]
    findings: tuple[str, ...]
    challenged_assertions: tuple[str, ...]
    missing_references: tuple[str, ...]
    unsupported_features: tuple[str, ...]
    counterfactual_objections: tuple[str, ...]
    benign_signals: tuple[str, ...]
    abstained: bool

class Flow(Strict):
    source_actor: Literal['TA', 'PA', 'EA', 'SCHEME']
    destination_actor: Role
    flow_type: Literal['contribution_dependency', 'hypothesized_benefit']
    claim: Claim
    trace_ids: tuple[str, ...] = Field(min_length=1)

class Gate(Strict):
    gate_id: str
    name: str
    passed: bool
    evidence: tuple[str, ...]
    reason: str

class Evaluation(Strict):
    evaluation_id: str
    fixture_id: str
    passed: bool
    checks: tuple[str, ...]
    trace_ids: tuple[str, ...]

class Card(Strict):
    pattern_id: str
    run_id: str
    scenario: Scenario
    source_manifest: dict[str, str]
    title: str
    summary: Claim
    actors: tuple[Role, ...]
    contributions: tuple[Contribution, ...]
    flows: tuple[Flow, ...]
    assertions: tuple[Claim, ...]
    limitations: tuple[str, ...]
    classification: Classification
    comparison_rationale: str
    counterfactuals: tuple[Counterfactual, ...]
    missing_data: tuple[str, ...]
    trace_ids: tuple[str, ...]
    evaluation_ids: tuple[str, ...]
    machine_outcome: Literal['PASS', 'BLOCKED']
    human_status: str = 'NOT_REVIEWED'

class Run(Strict):
    run_id: str
    run_type: RunType
    parent_run_id: str | None
    removed_actor: Role | None
    scenario: Scenario
    status: Status = 'RUNNING'
    version: int = 0
    depth: int = 0
    @model_validator(mode='after')
    def lineage(self):
        if self.run_type == 'CF':
            if not self.parent_run_id or not self.removed_actor or self.depth != 1:
                raise ValueError('CF requires candidate parent, removed actor and depth one')
        elif self.parent_run_id or self.removed_actor or self.depth:
            raise ValueError('Top-level run cannot have parent, removed actor or depth')
        return self

class Invocation(Strict):
    invocation_id: str
    context: Context
    raw_output: str
    outcome: str
    error_code: str = ''
    output_digest: str = ''
    semantic_output_digest: str = ''
    output_bytes: int = 0
    schema_version: Literal['2'] = '2'
    script_version: str = 'scripts-2'

class AuditEvent(Strict):
    event_id: str
    timestamp: str
    run_id: str
    trace_id: str
    kind: str
    actor: str
    payload: dict

class StepAnnotation(Strict):
    run_id: str
    step_id: str
    reviewer: str
    action: Literal['ACCEPTED', 'DISPUTED', 'REJECTED']
    rationale: str
    origin: Literal['human', 'model']
    candidate_run_id: str | None = None
    expected_version: int = Field(default=1, ge=0)
    explicit_action: bool = True

class HumanDecision(Strict):
    run_id: str
    reviewer: str
    origin: Literal['human', 'model']
    explicit_action: bool
    action: Action
    rationale: str = Field(min_length=15, max_length=2000)
    expected_version: int = Field(ge=0)
