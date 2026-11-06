# Control and regression traceability

This retained register explains security semantics and regression coverage in the source release.

## Correction and regression matrix

| Finding | Implemented correction | Executable regression coverage |
|---|---|---|
| F1 HIGH | `grounding.support`: versioned direct-MO/context/benign/unsupported mapping. All requested features retained. Unsupported mechanism returns NO_PATTERN before calls; gateway validates contribution citations and safety rechecks support. | `test_f1_*`: S5 single/dependency, mixed unsupported, S1/S2, S3/S4 context, unrelated valid IDs, valid MO hypotheses. |
| F2 HIGH | `dependency_graph` separates coverage and explicit consumed material features; validates earlier routed contributions, uses final contribution ancestry. `cf_outcome` distinguishes multi-party dependency, surviving coalition, single actor and inconclusive. | `test_f2_*`: disconnected partitions, two/three roles, removable nonessential actor, forged/self/future/unrelated/nonmaterial/duplicate edges, obsolete earlier cooperation. Existing fresh/reduced/incomplete CF tests retained. |
| F3 HIGH | `review.review` examines actors, material contributions, source support, quotation/provenance, assumptions, benign signals, uncertainty, CF objections and independently computed comparison. Safety rebuilds the trusted draft and validates findings. | `test_f3_*`: unsupported/missing references, factual claims, missing assumptions/uncertainty, wrong actors, inconclusive CF, benign signals, comparator disagreement and attempted approval. Existing denied lookup test retained. |
| F4 MEDIUM | Controlled feature-to-data mapping and nonempty, unique, relevant data validation; no investigative requirements for benign/no-pattern results. | `test_f4_*`: empty, blank, irrelevant, unsupported, duplicate and relevant requirements; benign abstention. |
| F5 MEDIUM | Annotation resolves actual persisted child lineage, verifies root ID/version and explicit human action/rationale, commits annotation plus root invalidation atomically. Prior decisions remain immutable. CLI accepts actual step run plus explicit candidate/version. | `test_f5_*`: child message rejection/invocation dispute/acceptance, unrelated/cross-candidate/stale/nonexistent steps, concurrent conflict, prior approval preservation, CLI and insert/COMMIT rollback. |
| F6 MEDIUM | Start plus consumption committed atomically; one terminal invocation per attempt, including denial, malformed/oversized output, timeout and adapter exception. Rejected bytes are hashed, not delivered or retained as raw diagnostics. Recovery closes interrupted starts. | `test_f6_*`: operation, schema retries, policy/unsafe denial, size, post-call timeout, exception, missing-terminal recovery and start-write rollback. |
| F7 MEDIUM | Denied decisions produce sanitized records after transaction rollback. Audit failure is explicit and cannot produce a success receipt. Successful state/decision/receipt remains one transaction. | `test_f7_*`: model/unknown reviewer/no action/rationale/stale, concurrent duplicate, insert/COMMIT failure and audit-store failure. Existing gate and approval action tests retained. |
| F8 HIGH | `semantic-replay-2` includes full meaningful records, pinned config, messages/dependencies, invocation/policy outcomes, cards/flows, reviews, CFs, gates and evaluation. Separate post-review form includes human semantics; export remains unchanged. | `test_f8_*`: fourteen single-field mutations, positive/negative/retry replay, post-review decisions and child annotations. Packaged sample replay checks retained. |
| F9 MEDIUM | `Store.create_run` uses BEGIN IMMEDIATE to check parent, participation, cap, distinct removal, all pinned snapshots and remaining call allocation; reservations prevent concurrent allocation overrun. Direct APIs have the same admission boundary. | `test_f9_*`: zero/full caps, duplicate/concurrent removal, concurrent last slot, changed scenario/limits/policy, invalid state/actor/depth, nonparticipant and exhausted budget. |
| F10 MEDIUM | Source-aware mechanism summaries and actor contribution/benefit text; explicit directed dependency and hypothesized benefit flows linked to actual trace IDs; MO shared/absent/additional concept rationale. | `test_f10_*`: distinct two-/three-/single-role/variation outputs, valid trace endpoints, MO differences and unsupported NEW abstention. |

All nine previously failed probe behaviours are reproduced in the dedicated remediation
modules. F9 now rejects before creating a child, so its regression expects a ValueError
and verifies unchanged usage/no child, rather than inspecting a completed invalid run.
The original verifier scripts remain outside the repository; this register does not claim
that their old expected API shape or old snapshot assumptions remain valid unchanged.

## Deliberate baseline changes

The 72 baseline cases remain collected. Three legitimate updates are explicit:

1. `new_relative` changes from REVIEW_PENDING/NEW to NO_PATTERN because S1/S2 supply
   weak context only. No grounded replacement is invented to preserve a positive demo.
2. The operation-denial test now requires one auditable terminal invocation instead of
   asserting the defect (zero persisted calls).
3. The independent full-feature synthetic adapter now supplies internally consistent new
   dependency metadata and matching safe prose. Its original BLOCKED, three-CF,
   all-INCONCLUSIVE and failed dependency-gate assertions remain intact.

## Before and after cards

| Example | Before | After |
|---|---|---|
| two_actor | Generic hypothesis and actor-name flow prose | Cash inducement/credit use/optional attendance, PA→TA material dependency, consumed features, trace-linked directed flow and relevant attendance/enrolment/value records; KNOWN MO-04. |
| three_role | Generic actor benefits; feature loss treated as dependence | Sponsor support/provider value return/employment concepts, PA→EA→TA contributions with explicit requirements; VARIATION shows shared, absent and additional MO-06/MO-08 features. |
| single_actor | Generic card | Unsupported-claim/nonattendance hypothetical mechanism, no peer dependency flow, explicit single-actor feasibility and relevant claim/attendance records. |
| variation | Generic partial match | Cash inducement/credit use with optional-attendance concept explicitly absent from MO-04 comparison. |
| new_relative | Positive NEW hypothesis from S1/S2 | NO_PATTERN and no card: every unsupported feature retained in the grounding diagnosis. |

## Architecture decisions and limits

Exactly TA/PA/EA/REV remain scripted adapters; ORCH and all controls are deterministic.
The shared gateway and CANDIDATE/CF/TEST separation are unchanged. Schema v2 adds
consumed-feature dependency records, structured flows and reviewer findings. The explicit
SURVIVING_COALITION verdict refines the v3 design's broader structural categories and does
not imply single-actor sufficiency or three-role necessity. Inconclusive evidence blocks.

CF admission pins the persisted parent scenario/seed, source manifest, policy, code, schema,
script version, grounding version and limits; a caller cannot replace the cap. It reserves
baseline remaining actor calls, while retries must still fit unreserved aggregate capacity.
Denied admission creates no executable child or model call. An admitted failed CF is not
reused to replenish the parent's cap. Direct admission errors are surfaced to the trusted
caller; normal scheduling records them as inconclusive admission evidence.

All annotation actions require a rationale. ACCEPTED never approves; every annotation bumps
the originating candidate's version. One step cannot be silently overwritten. Material
rejections/disputes preserve messages and historical decisions, record invalidation, and move
pending/approved candidates to REVISION_REQUESTED while preserving already blocked states.

Invocation SCHEMA_VALID denotes a completed validated response (actor responses also passed
receipt/safety). The reviewer may still fail independent semantic gates. Rejected outputs have
byte and ID-normalised semantic hashes, byte counts and reason codes. An abrupt process loss
can leave a started call; recovery records INTERRUPTED, never a fabricated successful output.
Synchronous elapsed checks cannot cancel a hung adapter.

The canonical simulation form excludes human-only records and uses the last machine state;
the post-review form includes annotations, decision semantics and current state/version.
Generated identifiers are mapped with preserved references, clocks/global sequence numbers
are omitted, and byte hashes are represented by their ID-normalised semantic hash. Shared
budget usage is scoped to this execution to avoid unrelated experiment interference. Neither
form is a cryptographic audit seal. Pinned code changes intentionally change replay identity.

No Part 1/2A/2B files or historical verification claims are rewritten. Native Mermaid rendering,
enterprise authentication, malicious-host sandboxing and real-model empirical evaluation remain
outside the demonstrated scope. Current counts and commands are in [evaluation_report.md](evaluation_report.md).

