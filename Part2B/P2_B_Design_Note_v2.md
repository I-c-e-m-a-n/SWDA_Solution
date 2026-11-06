# SWDA Part 2B — Multi-Agent Fraud-Risk Simulation: Principal Engineering Design Note

**Version:** 2.0 (targeted independent-review correction)  |  **Date:** 6 November 2026  |  **Status:** Proposed local Python proof-of-concept design; implementation and runtime assurance **not verified**  
**Design baseline:** Part 2A v3 executive overview, detailed component architecture, six-phase execution sequence and accompanying notes.  
**Assessment:** SWDA ML/AI Engineer Take-Home Assessment, Part 2, Annexes A and B.  
**Decision scope:** Hypothetical risk patterns for **human consideration of further investigation**, never a fraud finding.

## 1. Executive design summary

The SWDA case study asks whether a controlled multi-agent system can explore hypothetical misuse of training grants involving trainees, training providers and employers, then present intelligible risk patterns to a human. It does **not** ask an automated model to adjudicate claims. The available material consists only of eight *illustrative* modus operandi (MO) entries in Annex A and five exercise-written, unverified social-media excerpts in Annex B; S5 is a benign counterexample. Neither set establishes that misconduct occurred.

The proposed **local Python proof of concept**, illustrated in the Part 2A v3 architecture and sequence, places a trusted loader and read-only, provenance-labelled catalogue ahead of a deterministic orchestrator. A single policy/schema gateway mediates scoped messages to and from three isolated **scripted mock** actor agents. The orchestrator fixes actor permissions, source visibility, turn order and budgets. Trusted analysis assembles structured, hypothetical pattern cards and runs one-level actor-removal counterfactuals to test dependence *inside the simulation*. A separate, less-trusted Review Agent may challenge assumptions and consult allowlisted MO/source references through that same gateway; it cannot approve cases or access the catalogue directly.

Independent deterministic safety and evaluation gates must pass before an eligible **CANDIDATE** enters persisted `REVIEW_PENDING`. An authorised human then chooses to approve *for investigation*, reject or request revision; a trusted service is designed to commit the decision and status atomically in SQLite. Dedicated **TEST** runs exercise regressions but cannot enter the approval queue. Typed provenance, bounded execution, traceable decisions and fail-closed controls make the design auditable and testable. These are **architectural commitments**, not demonstrated runtime protections or measured detection performance.

## 2. Assessment context, scope and assumptions

The assessment requires distinct actor profiles, controlled interaction, least-privilege access, structured risk cards, actor-removal comparisons, explicit evidence labels, sample-relative MO classification, schema/budget control, guarded human approval and replayable evaluation. Qualities of particular importance are **safety, reproducibility, traceability, predictably bounded resource use and truthful uncertainty**. The corresponding Part 2C deliverable must be runnable, with a one-command setup, scripted mocks, tests, traces and sample cards; none is implied by this Design Note.

Annex A contains `MO-01`–`MO-08`, expressly a *sample* library rather than SWDA's actual inventory. Labels such as “Observed”, “Observed overseas” and “Policy risk” are inherited assessment metadata, **not independently verified findings**. Annex B comprises `S1`–`S5`, written for the exercise and unverified. S1 raises course-description concerns; S2 raises perceived price/value concerns; S3 describes an alleged inducement; S4 raises concerns about pass rates; S5 describes a useful course. These are *signals to examine*, not confirmations of misconduct. No websites, live grant/claim records or personal data supplement them.

| Statement | Basis | Engineering implication |
|---|---|---|
| Three simulated actor roles, one Review Agent, orchestrator and human approval | Assessment requirement | Preserve assigned roles and human-only decision authority. |
| Annex A is illustrative; Annex B is unverified | Assessment | Display source type and uncertainty on every applicable assertion. |
| Source digests are checked against a separately trusted versioned manifest | Part 2A v3 design choice | Implement and test independent expected-value distribution; a matching hash does not validate factual truth. |
| Role-specific source subsets, recipients and simulation incentives | Configurable PoC assumptions | Freeze the scenario access-control list (ACL) and record it per run; do not claim these are SWDA operational permissions. |
| Scripted mock responses, SQLite persistence and local reviewer identity | PoC design choices | Suitable for a thin local slice; do not equate with live-model quality, enterprise identity or tamper-resistant storage. |

**Exclusions:** AWS/Databricks integration, mandatory Model Context Protocol (MCP), external model APIs, live SWDA cases, real applicant data, fraud enforcement, production identity management and additional autonomous agents. The separately documented Part 1A architecture is not a dependency.

## 3. Architecture overview, decisions and rationale

Read the **executive overview** (`P2_A1_Executive_Overview_v3.mmd`) for end-to-end boundaries, the **detailed component diagram** (`P2_A1_Simulation_Architecture_v3.mmd`) for permission/data/audit paths, and the **six-phase sequence** (`P2_A2_Simulation_Sequence_v3.mmd`) for ordering and exceptional branches. They are complementary architectural views, not additional implementations, consistent with C4, arc42 and Microsoft's purposeful-diagram guidance [E1–E3].

The untrusted `SRC` annex text enters trusted `LOAD`, which checks IDs, schema, version and bytes against expected SHA-256 digests from a **separately trusted, review-controlled manifest**. `CAT` serves a pinned, read-only catalogue labelled with source IDs and provenance. `INIT` and trusted `ORCH` configure run type, seed, scenario, turns and cumulative budgets. `OUT`/`IN` are **two facets of the same gateway**, which A2 abbreviates as `POL`; `CTX` constructs per-role views without unauthorised history. `TA`/`PA`/`EA` are isolated scripted mocks, not trusted policy engines.

`CARD` produces bounded hypothetical cards; `DEP` requests an independent linked counterfactual through `ORCH`; `MO`/`REF` perform **trusted read-only** reference work. Less-trusted `REV` only recommends a classification. A1's reviewer path `REV → OUT → MO/REF → IN → REV` is A2's `REV → POL → CAT → POL → REV`, with A2 `CAT` encompassing the trusted helpers; **there is no direct reviewer-to-catalogue permission**. `GATE` (A2 `SAFE`) and `EVAL` provide independent code-gated assurance. `UI`/`DEC` capture a human-origin request; `APPROVAL` (A2 `APPR`) owns the state transition. `STATE`, `EVENTS`, `TRACE` and `DECISION` are logical functions consolidated into A2 `STORE`, not separate enterprise databases.

Solid arrows denote structured **data**, long-dashed arrows denote **control/authorisation**, and dotted arrows denote **audit/telemetry**. A1's `REV → EVENTS` audit arrow is a **conceptual event emitted by trusted invocation wrappers**, not agent permission to mutate audit records. No model output is a trusted state-write instruction.

| Decision / alternative | Reason for selected design | Cost, risk and verification obligation |
|---|---|---|
| Deterministic `ORCH` rather than agent-led planning | Keeps scheduling, policy and termination outside generated text. | Less flexibility; prove timeout, resource caps and state transitions in code. |
| One mediated `OUT`/`IN` gateway rather than peer channels | Makes sender/recipient ACL, schema and source scope consistently enforceable. | Central control point; test both directions, denials and failure defaults. |
| Scripted, separately scoped actors rather than one generalist model | Exposes role-dependent hypotheses and attributable message contributions. | More orchestration and synthetic realism risk; compare against a single-agent baseline later. |
| Independent `REV` plus deterministic `GATE`/`EVAL` rather than model-as-authority | Permits critique without granting models security or approval authority. | More components and inconsistent outputs to manage; test review denial and gate independence. |
| Versioned annex snapshot and SQLite rather than live systems | Reproducible, small, inspectable local proof of concept. | Manifest provenance, database locking/atomicity and audit integrity still need evidence. |
| Human-only `APPROVAL` rather than automatic publication | Prevents hypothesis from becoming a consequential decision unaudited. | Manual workload and possible reviewer bias; verify reviewer authority and stale-request handling. |

## 4. Actor profiles and least privilege

All incentives below are **scenario hypotheses**, motivated only by assigned roles and the illustrative annexes. The allowed source IDs and recipient ACLs are **configuration values still to be fixed in Part 2C**, not facts about actual participants.

| Agent | Hypothetical objective, capability and visible information | Recipients and permitted tools | Prohibitions, boundary and enforcement |
|---|---|---|---|
| **Trainee** (`TA`) | Model a possible trainee benefit or reduced effort; propose/reply with typed, abstract messages. Sees its profile, scenario-allowlisted Annex IDs and previously validated messages addressed to it. | Configured Provider and/or Employer **through `ORCH`/`POL` only**; scripted `propose_message`/`reply_message`. | No real enrolments/claims, private peers' context, source edits, direct peer calls or audit/approval writes; enforce bound sender, permitted recipient, source scope, safe content, schema and budget. |
| **Training Provider** (`PA`) | Model possible enrolment/funding incentives, described only as risk-level hypotheses; sees its scoped source subset and authorised prior messages. | Configured Trainee and/or Employer via gateway; typed scripted proposals/replies. | No alteration of attendance, invoices, grants or catalogue; fixed provider ACL, message schema and resource limits. |
| **Employer** (`EA`) | Model hypothetical employer involvement/benefit; sees a configured annex subset and validated messages intended for this role. | Configured Trainee and/or Provider via gateway; typed scripted proposals/replies. | No payroll, hiring, claim-system access, unapproved retrieval, direct actor links or trusted-state mutation; enforce exact identity/recipient/source and limits. |
| **Review Agent** (`REV`) | Challenge candidate claims, evidence strength, benign counter-signals, missing test data and known/variation/new **relative to MO-01–MO-08**; sees a tagged card and approved, filtered reference results. | Read-only `reference_lookup(source_ids, purpose)` through `OUT`/`IN` (`POL`); emits recommendations to trusted assurance (`GATE`/`EVAL`), not peers. | No raw `CAT` browsing, arbitrary tools, private actor state, changed ACL, independent policy enforcement, `REVIEW_PENDING` write or approval; require reviewer identity/purpose binding, allowlisted ID intersection, response filtering and denial audit. |

The reviewer requires broader **cross-reference** access than any simulated actor, but that does not confer broader authority: the gateway performs purpose-specific read checks and trusted helpers return only filtered material. A single role, two roles or all three may participate in a particular *scenario*. The presence of three configured actors does **not** prove three-party collusion. All permissions are fixed by trusted configuration, not prompt assertions.

## 5. Six-phase execution and exceptional behaviour

| Phase and initiator | Inputs → outputs and trust crossing | Validation, state and termination | Trusted audit evidence |
|---|---|---|---|
| **1. Initiation and source trust**; human `H` via `CLI`, then `ORCH` | Versioned scenario, selected annex IDs, seed and ACL → new `CANDIDATE`, verified pinned snapshot. `CAT` integrates `LOAD`. | Compare schema, ID, version and digest with independently trusted manifest; install permissions and caps. Invalid, missing or altered input → `BLOCKED`, quarantine and **no dispatch**. Initial state is non-approved. | Manifest/version/digests, scenario, ACL, seed, run ID, validation failures and resource limits. |
| **2. Bounded simulation**; `ORCH` | Per-role excerpts and typed envelopes → validated transcript. Every request/reply crosses `POL` (`OUT`/`IN`). | Check sender, recipient, permitted IDs, schema, safety and remaining rounds/turns/time/calls. Retry **schema** errors only with identical scope; policy denial fails closed; timeout or exhausted caps → `BLOCKED`/incomplete. Seal completed transcript before analysis. | Dispatch/receipt allow-deny, message IDs, rounds, retry/fault codes, usage, checkpoints and terminal status. |
| **3. Hypothetical pattern construction**; `ANA` (`CARD`/`DEP`) | Completed transcript → tagged card(s) and linked actor-removal `CF` outcomes; same gateway for survivors. | Up to three cards and at most three depth-one CFs, each tied to a participating actor; fresh context, taint removal and parent/seed/ACL pinning. No CF recursion. Failed/incomplete CF → record **inconclusive**, not fabricated dependence. | Card IDs, assertion tags, CF parent/child IDs, removed actor, scoped snapshot and result/fault references. |
| **4. Independent review and assurance**; `ANA` to `REV`, then `SAFE`/`EVAL` | Tagged card and filtered read-only references → non-binding classification plus independent gate report. Reviewer lookup crosses `POL` and trusted `CAT` helper boundary. | Invalid reviewer ACL/source → invalid review. `SAFE` checks provenance, schema, injection and unsafe detail; `EVAL` checks candidate-linked actor/end-to-end (E2E) assertions. Failed gates → blocked diagnostics; **passing CANDIDATE only** → persisted gates + `REVIEW_PENDING`. | Read allow/deny, review rationale and uncertainty, evaluation IDs, pass/fail gates, trace linkage. |
| **5. Human-only decision**; `H` via `CLI` | Tagged, non-factual risk card, gate evidence and explicit action/rationale → trusted `APPR` request. | `APPR` checks local/configured reviewer role, current `REVIEW_PENDING`, persisted passes and one of three actions; proposed SQLite compare-and-swap (CAS) commits status and decision **in one transaction**. Stale/model-originated/malformed attempts fail without state change. | Reviewer ID, role-verdict, rationale, expected state/version, decision ID, timestamp, outcome and **post-commit** receipt or denial. |
| **6. Separate TEST evaluation and observability**; `EVAL` | On-demand/pre-submission suite → independent top-level `TEST` runs via same `ORCH`/`POL` route. This is **not** a child of Phase 4 candidates. | Benign, injection, malformed and denial fixtures under separate per-fixture and suite limits. No CF/TEST descendants, human queue or approval-state mutation. Fixture failure/incomplete suite produces an explicit report, not automatic approval or recursive retrigger. | Fixture/run IDs, expected vs actual policy outcomes, versions/seeds, usage, events and regression report. |

The phases are the sequence diagram's presentation order, **not evidence of a single end-to-end run having executed**. Phase 4 includes **candidate-linked** evaluation of its trace and relevant gate evidence; Phase 6 describes **separately invoked** TEST fixtures. Their evidence may be linked by trusted code, but TEST results do not acquire authority to approve a candidate. The **only permitted human request actions** are `APPROVE_FOR_INVESTIGATION`, `REJECT` and `REQUEST_REVISION`, mapped respectively to persisted outcomes `APPROVED_FOR_INVESTIGATION`, `REJECTED` and `REVISION_REQUESTED`. `APPR` requires an explicit locally authorised human request and rationale, committed passing gates and the current `REVIEW_PENDING` state before its atomic compare-and-swap transaction. A revision request **does not automatically rerun** the case.

### Run-type and budget contract

| Run type | Parent/derivation | Eligibility and authority |
|---|---|---|
| `CANDIDATE` | Top-level selected scenario | At most **3 cards**; only completed and gate-passing candidates may become `REVIEW_PENDING`. |
| `CF` | `parent_run_id` **must** reference a `CANDIDATE`; `removed_actor_id` required; depth **exactly one** | At most **3 per candidate**, one per distinct participating role; no CF/TEST children, no approval queue. |
| `TEST` | Independent top-level fixture, not a CF/candidate descendant | At most **12 fixtures per suite**, no children, never human-approvable. |

**Proposed configuration defaults, not observed limits:** per run **4 rounds**, **12 actor turns**, **2 schema retries per message**, **120 seconds elapsed**; **48 total scripted-mock calls** shared by each `CANDIDATE` and all its CFs; per TEST fixture **12 mock calls** and per suite **60 aggregate mock calls**. All local and aggregate restrictions apply simultaneously; the suite may exhaust 60 calls **before** executing all 12 fixtures. Check limits **before** scheduling each call or retry; no child run or schema retry replenishes the parent's budget.

## 6. Structured handoffs and pattern-card contract

Each dispatch/response uses a **proposed** typed envelope with `run_id`, `run_type`, `parent_run_id` where applicable, `message_id`, `parent_message_id` for routed continuations, `round`, `turn`, `sender_role`, `recipient_role`, `purpose`, permitted `source_ids`, source and ACL/policy versions, `schema_version`, provenance tags, payload and budget/attempt metadata. Trusted code binds actor identities and permissions; agent-supplied identity, source IDs or recipient expansions cannot supersede the envelope. Duplicate IDs, missing required fields, unallowed recipient/IDs, unsafe content and malformed structure produce typed denials; limited schema retries use the **same** original scope.

The card schema should hold `card_id`, originating `run_id`, scenario/version, **participating** actor list, each actor's abstract contribution, purported benefit and conceptual flow, cited Annex IDs, per-assertion `SOURCE` / `SIMULATION` / `ASSUMPTION` type, provenance strength and uncertainty, MO comparison and rationale, actor-removal results and linked trace IDs, additional records needed for empirical testing, validation outcome and reviewer recommendation. `SOURCE` means attribution to annex text, **not confirmation**; `SIMULATION` means scripted behaviour, and `ASSUMPTION` is model configuration or inference. No output is permitted to become a detailed fraud playbook.

**Known**, **variation** and **new** mean resemblance, variation or absence of a sufficiently close match **within the eight supplied sample MOs only**. “New” is never a claim of novelty to SWDA or the real world. **A denied or invalid `REV` reference lookup is a mandatory `SAFE` gate failure**: the review is invalid, the CANDIDATE remains blocked and cannot enter `REVIEW_PENDING`. There is no fallback to unrestricted catalogue access. By contrast, *after a successfully authorised lookup*, weak grounding, ambiguous sample similarity, incomplete counterfactual evidence or benign counter-signals may justify an **inconclusive** or rejected card, subject to deterministic gates; an inconclusive recommendation is **not automatically a passing candidate**. The v3 sources do not settle the exact threshold for accepting an inconclusive CF, which Part 2C must specify and test. Required empirical data may be described by *category*, such as independently verified enrolment, attendance or claim records, without fetching them in this PoC.

## 7. Actor-removal analysis and collusion distinction

A coherent exchange involving several scripted roles may only reflect their prompts. Actor removal asks a narrower, falsifiable simulation question: *does the candidate pattern still appear when one participating role and the information dependent on it are excluded?* `DEP` submits a linked `CF` request to `ORCH` using the candidate ID, removed actor, pinned annex manifest/digests, scenario seed, ACL snapshot, budgets and dependency map. `ORCH` allocates a fresh run ID, omits the role from scheduling and rebuilds remaining actors' context from the immutable source baseline. It must remove that actor's messages **and every downstream message that depends on them**; simply deleting a name from a completed transcript is invalid. Survivors execute through unchanged gateway/schema controls and share the parent's aggregate mock-call cap.

Comparison can support **multi-party structural dependency** (a pattern demonstrably depends on contributions from multiple participating roles), **single-actor feasibility** (the relevant contribution is attributable to one role without material dependence on others), or **inconclusive** (insufficient contributions, budget exhaustion, unstable outputs or failed checks). **One actor-removal run from a three-role candidate leaves two roles and cannot, by itself, establish single-actor feasibility.** The verdict must therefore combine the role-contribution/dependency graph with the bounded CF results; a zero-contribution or non-participating role is not counted as evidence of collusion. Proposed checks cover single-, two- and three-role fixtures, including an apparently multi-party candidate that remains plausible after removal and an inconclusive CF. These are model-specific structural classifications: survival is not evidence of real misconduct, and degradation is not real-world causal proof. Fixed seeds support scripted replay; future stochastic models require repeated trials and sensitivity analysis. CF failures remain traceable and are never reviewable candidates themselves.

## 8. Security, safety and governance

This is a **defence-in-depth design**, not a claim that prompts, diagrams or static schemas enforce security. Untrusted annex content is data, not system policy; instruction hierarchy, structured context and safe output instructions help behaviour but **cannot confer authority**. Identity binding, access checks, strict parsers, budgets, state transitions and approved tool contracts must be implemented in trusted Python code, consistent with OWASP's emphasis on least privilege and tool-boundary validation [E4].

| Threat | Proposed enforceable control | Negative Part 2C test / expected result |
|---|---|---|
| Annex-sourced indirect prompt injection or encoded instructions | Trusted expected digest, data/instruction separation, bounded decoding, scope checks and constrained model output. Suspicious content may remain available **as inert, attributed data** unless a separate content-policy rule excludes it. | Injected text cannot change policy, tools, recipients or approvals; log attempted influence and deny *unauthorised actions or unsafe output*, rather than automatically denying the source solely for containing instruction-like words. |
| Forged sender/recipient or cross-actor leakage | `ORCH` binds principal and recipient; gateway checks per-role ACL and scoped `CTX`. | Spoofed identity, unauthorised recipient or tainted prior message → deny without delivery. |
| Unauthorised source lookup by `REV` | Narrow `reference_lookup` via `POL`; trusted `MO/REF` (`CAT` in A2) and filtered results. | Out-of-scope ID/purpose/direct-catalogue request → denial and invalid-review gate. |
| Retry-based escalation or budget bypass | Immutable retry envelope; pre-call local and aggregate quota enforcement. | Retry with extra source/recipient or beyond cap → fail closed and preserve original ACL. |
| Recursive CF/TEST runs | Run-kind state machine; CANDIDATE-only CF, depth one; independent non-recursive TEST. | CF→CF, CF→TEST, TEST→TEST or TEST→CF attempt → rejection. |
| Unsupported factual allegation or operational fraud detail | Typed source tags, abstract pattern schema, deterministic unsafe-detail checks and human warning. | Mock makes factual or procedural claim → reject/quarantine card; no public finding. |
| Reviewer/gate bypass and mock approval attempts | Review has recommendation-only rights; gate writes restricted to trusted `SAFE`; only `APPR` commits decisions. | `REV`/`EVAL`/actor sends `APPROVE_FOR_INVESTIGATION` or a gate-write request → denied, state unchanged. |
| Stale, conflicting or unreasoned human decision | Local/configured reviewer check, required reason, persisted gates and SQLite CAS in one transaction. | Two simultaneous decisions, stale version or induced commit failure → at most one valid commit, no false receipt. |
| Altered annex or trusted-manifest file | Compare bytes with pinned expected digests in separately reviewed release metadata; restrict and verify manifest changes outside the untrusted annex channel. A fully compromised trusted release/manifest root is **not detectable by comparing the two attacker-controlled values**. | Changed annex, missing expected value or unauthorised manifest change *against a protected expected release snapshot* → block/quarantine. Test the trust-anchor boundary; do not claim detection of a jointly compromised annex and release manifest. |
| Audit alteration or loss | Trusted event writers, separate decision transaction, restricted agent capabilities and recovery checks. | Agent attempts record edits → denied; interrupted write/restart → detect gaps or report missing evidence. |

**Fail closed** means a failed identity, policy, source-integrity or required provenance check never grants access or promotes state. A schema retry is not a fresh authorisation. Prompt-level role reminders and suspicious-text screening are supplementary only; exact permissions and high-consequence decisions reside outside the model. A locally append-only trace is **not tamper-proof** against a privileged operating-system user. Future cryptographic audit assurance or enterprise authorisation would be separately scoped, not silently added here.

## 9. Evaluation methodology and acceptance evidence

Following the NIST generative-AI risk-management emphasis on documented risk and measured controls [E5], `EVAL` examines **actor-level handoffs** and **candidate-linked end-to-end trace/gate evidence** in Phase 4; in Phase 6 it drives isolated, top-level **TEST-only** runs through `ORCH`/`POL`. `EVAL` has **no approval-service invocation or state-write permission**. Negative approval-authorisation and SQLite concurrency cases belong to **separate trusted Part 2C integration tests of `APPR`**, using synthetic human-origin test requests; they are not TEST agents or fixtures entering the review queue. For scripted mocks, expected outcomes are reproducible assertions, not statistical detection claims. All criteria below are **proposed**; no accuracy, latency, safety or transaction result has been measured.

| Dimension | Mechanism and proposed criterion |
|---|---|
| Typed messaging and schema | Property-based/fixture validation of legal and malformed envelopes; all mandatory-field, recipient, version and duplicate-ID violations denied. |
| Source grounding/provenance | Exhaustive allowlisted ID and digest-mismatch fixtures; only permitted `MO-01`–`MO-08`/`S1`–`S5` cited; every substantive card assertion carries a tag. |
| Actor ACL and isolation | Cross-role sender/recipient/source spoofing tests; no unauthorised message delivered or unscoped data exposed. |
| Execution bounds and recovery | Round/turn/retry/time/local-and-aggregate-call boundary tests; never execute an over-budget call; failed/incomplete run stays unreviewable. |
| Policy denial and injection | Benign and adversarial strings, including instructions embedded in source content; forbidden tool/scope use denied, with reasoned event. |
| CF correctness | For single-, two- and three-role fixtures, remove each participating role within the cap; assert valid parent/child IDs, unchanged pinned settings, fresh context, descendant-taint pruning, depth one, comparisons grounded in actual contributions, and inconclusive handling when runs fail. |
| Sample-relative MO classification | Pre-adjudicated **annex-only** synthetic test fixtures for known, variation, new-relative-to-sample and inconclusive; check the declared matching rationale, evidence/source IDs, distinguishing differences and missing validation data. Record per-class counts and disagreements/abstentions; no accuracy score is claimed without an executed suite. |
| Benign false positives | S5-focused controls and benign mixed scenarios; S5 alone must not be treated as evidence of fraud or produce a factual allegation. |
| Approval protection and SQLite CAS | **Trusted `APPR` integration tests**, not EVAL-triggered TEST executions: reject CF/TEST or model-origin requests, absent rationale, unauthorised local role and stale versions; exercise concurrent CAS/rollback. Expect no unauthorised state mutation and a post-commit receipt only for one accepted transition. |
| Replayability and observability | Same seed/versions/mock fixtures reproduce the specified structured outcomes and event linkage; no missing required identifiers. |
| Fault and interrupted-run handling | Missing manifest, denied reviewer lookup, malformed output, budget exhaustion and interrupted transaction yield explicit blocked/incomplete state and diagnosis. |

Candidate-linked checks occur during Phase 4. Independent **top-level TEST** suites occur in Phase 6 and cannot mutate candidate decisions. The suite should include benign, adversarial, malformed-schema and explicit permission-denial fixtures. Proposed deterministic security criteria are *zero unauthorised transitions in the designed negative fixtures* and *complete evidence fields for every accepted transition*, but those are **requirements**, not achieved rates.

Scripted mocks cannot prove spontaneous collusive discovery, realistic incentives, novelty, causal necessity or quality with real language models. A **future, separately approved real-model evaluation** would require expert-authored benchmark cards and independent adjudication labels, blinded multi-reviewer ratings, inter-rater agreement, benign/control prevalence, adversarial perturbations, calibration/abstention measurement and error analysis across seeds and model versions. Measure false positives, unsupported-source claims, unsafe-detail incidence and robustness **before** choosing acceptance thresholds; do not infer them from these diagrams or import external fraud evidence into this assignment.

## 10. Observability, reconstruction and audit

The proposal separates **run state** (`STATE`/A2 `STORE`), **trusted execution events and traces** (`EVENTS`/`TRACE`), and **atomic human decision records** (`DECISION`). An event schema should identify `event_id`, timestamp, event type, run/trace ID, `run_type`, `parent_run_id`, `removed_actor_id`, scenario/config/source-manifest versions, expected digests, permitted source IDs, seed, policy/ACL snapshot, **schema and scripted-mock adapter versions, deterministic fixture/version and code revision**, actor, round, turn, `message_id`, `parent_message_id`, schema outcome, allow/deny reason code, retry, elapsed time and mock-call usage. Analysis events add `card_id`, assertion provenance and CF outcome; reviewer-lookup events add an invocation ID, bound purpose, requested versus returned source-ID sets and filter/denial codes; assurance events add reviewer classification, `fixture_id`, `evaluation_id`, fixture expectation/version, gate evidence IDs and failure reasons. A decision record adds the human reviewer identifier, verified local role, action, rationale, expected-versus-committed status/version, decision ID, commit timestamp and receipt/error.

An engineer reconstructs a candidate by locating its `run_id`; reading the immutable scenario and source hashes; replaying scheduled actor turns and validated message ancestry; examining denied deliveries, retries, limits and card assertions; following child CF IDs to compare independently reduced outcomes; inspecting Review Agent lookups and `SAFE`/`EVAL` gate evidence; and finally matching `REVIEW_PENDING` with the committed SQLite decision transaction and human receipt. A `TEST` trace is independently identified and cannot be mistaken for that candidate lineage.

Suggested operational signals are denial counts by policy reason, schema-retry rates, blocked/incomplete runs, call usage versus caps, source-integrity failures, gate failures, fixture regressions, missing trace links and decision CAS conflicts. **Replay is valid only if the exact script/fixture versions, source snapshots, policy/ACL, deterministic dispatch order and recorded inputs are available**; a seed alone does not guarantee reproducibility. Logging should minimise sensitive payloads and preserve source-ID references instead. OpenTelemetry-style spans, attributes, events and links could model run/CF relationships [E6], but **OpenTelemetry is not claimed installed**. Append-only is an application-level intention, not cryptographic or administrator-proof immutability; trace-write and recovery behaviour require tests.

## 11. Multi-agent versus single-agent alternative

| Dimension | Separate scripted actors with central orchestration | Single-agent alternative |
|---|---|---|
| Role fidelity | Distinct prompts, profiles and access envelopes clarify hypothesised incentives. | Role switching is easier but may blend viewpoints. |
| Information separation | Enforceable per-role source/recipient scopes in trusted code. | One context more readily conflates access scopes. |
| Actor removal | Clear role-specific reruns and message ancestry. | Removing one simulated persona is a weaker isolation experiment. |
| Traceability | Attribution by actor/turn/message/CF. | Fewer traces, but individual role contributions are less separable. |
| Reasoning flexibility | Role interactions may expose alternative narratives; can also reinforce errors. | Simpler synthesis may be sufficient for narrow sample comparisons. |
| Realism | Simulates interaction, **not authentic human behaviour**. | Less interaction realism, but possibly fewer artificial feedback loops. |
| Hallucination/unsafe amplification | Cross-role reinforcement and prompt contagion require gateway checks. | Smaller attack surface, but still vulnerable to unsupported output. |
| Implementation complexity | More ACLs, contexts, lineage states and failure branches. | Cheaper to build, reason about and secure. |
| Cost and latency | Repeated actor/CF calls increase bounded work. | Usually fewer calls and shorter execution. |
| Reproducibility | Deterministic mocks and pinned contexts permit explicit replay. | Easier to replay but less granular causal comparison. |
| Testing/debugging | Stronger component attribution; larger interaction test matrix. | Easier unit and E2E tests; narrower role-isolation evidence. |
| Governance | Explicit trust zones and human-only approval. | Same critical external gates still required. |

**Judgement:** The actor-based architecture is justified here because the assignment specifically tests controlled role boundaries, orchestrated handoffs and actor-removal logic. It is **not inherently superior** at identifying fraud. A single-agent baseline is a sensible future cost/quality comparator; without empirical evaluation, claims of better accuracy or creativity would be unwarranted.

## 12. Limitations, residual risks and Part 2C obligations

| Residual risk / uncertainty | Required implementation or verification evidence |
|---|---|
| Scripted mocks do not demonstrate emergent reasoning or realistic collaboration. | Runnable mock adapters, deterministic expected cards and a separately planned real-model study. |
| Illustrative MOs and unverified excerpts cannot substantiate allegations; S5 is benign. | Provenance-tagged sample cards, benign fixtures and expert review of uncertainty wording. |
| Sample MO library is not the actual SWDA inventory; “new” is relative. | Tests asserting sample-only comparison and explicit output caveat. |
| CF structural findings depend on modelling choices, contribution attribution and taint accuracy; a three-role one-removal result cannot by itself prove sole-actor sufficiency. | Single-/two-/three-role fixtures, parent/child replay, contribution/dependency consistency, taint unit tests and incomplete/timeout handling. |
| Trusted expected-digest manifest is specified but not supplied as an implemented control; release-root compromise is outside simple digest comparison. | Reviewed/protected release snapshot, independent digest comparison, altered source and unauthorised manifest-change tests; explicitly document trust-anchor compromise limitation. |
| Reviewer role and SQLite CAS are proposed; identity and race safety are unproved. | Local role configuration, adversarial approval requests, concurrent CAS and forced rollback tests. |
| Gateway, policy scopes, schemas and ledger are design contracts, not executing code. | Exact ACL/schema fixtures, negative permission tests, audit-write restriction and bounded reruns. |
| Native Mermaid parser/render fidelity remains outstanding. | Mermaid CLI or browser-native validation of all v3 `.mmd` views and visual inspection. |
| Evaluation effectiveness, classification thresholds, inconclusive-CF gate handling and audit tamper-resistance are unmeasured or unresolved. | Pre-adjudicated positive/negative/inconclusive fixture matrix with expected outcomes, explicit CF gate rule, regression reports, trace completeness/replay checks, restart tests and privileged-admin limitation. |

These gaps are **implementation obligations**, not reasons to assume a design failure or to claim a security pass. The v3 static verification report supports structural/source-derived checks only. No production identity, live grant access, real fraud discovery or tested SQLite transaction behaviour is established.

## 13. Assessment requirements traceability

| Part 2 requirement | Design Note | v3 architecture / sequence | Part 2C evidence needed | Status |
|---|---|---|---|---|
| 1. Distinct actor profiles | §§2, 4 | `TP/PP/EP`, `TA/PA/EA`, `CTX`; Phases 1–2 | Versioned profiles, per-role context tests | Designed; runtime **not verified** |
| 2. Controlled inter-agent messages | §§3–5 | `ORCH`, `OUT/IN` = `POL`; Phase 2 | Routed message traces, forbidden peer-delivery tests | Designed; runtime **not verified** |
| 3. Code-enforced least privilege | §§4, 8 | Actor trust boxes, gateway; Phases 2, 4 | Denied source/recipient/tool fixtures | Designed; runtime **not verified** |
| 4. Structured patterns, benefits, flows | §6 | `CARD` = `ANA`; Phase 3 | Typed sample cards and schema assertions | Designed; runtime **not verified** |
| 5. Actor removal and collusion distinction | §7 | `DEP ↔ ORCH`, CF; Phase 3 | Fresh reduced runs, taint and non-recursion tests | Designed; runtime **not verified** |
| 6. Separate source/simulation/assumptions | §§2, 6 | `LOAD/CAT`, `CARD`; Phases 1, 3 | Verified source tags and non-factual output checks | Designed; runtime **not verified** |
| 7. Sample-relative MO classification and test data | §§4, 6 | `MO/REF/REV`, `POL`; Phase 4 | Classification fixtures, rationale/missing-data checks | Designed; runtime **not verified** |
| 8. Schemas, retries, rounds/cost | §§5–6, 8 | `ORCH`, `OUT/IN`, `STATE`; Phases 1–2 | Boundary/timeout/retry tests and aggregate counters | Designed; runtime **not verified** |
| 9. Injection/unsafe-output safeguards and human approval | §§5, 8 | `SAFE`, `APPROVAL/APPR`, `STORE`; Phases 4–5 | Adversarial fixtures; local role/CAS concurrency tests | Designed; runtime **not verified** |
| 10. Traces, evaluation and regression | §§9–10 | `EVAL/FIX`, `EVENTS/TRACE/STORE`; Phases 4, 6 | Runnable suite, correlated traces, fixture reports | Designed; runtime **not verified** |

## 14. Conclusion

Part 2A v3 is a defensible **design basis** for a narrow local, annex-only, scripted multi-agent PoC. Its strongest choices are deterministic orchestration, one consistently mediated gateway, explicit provenance and actor isolation, bounded counterfactuals, independent machine gates and a human-only decision transaction. These make hypotheses explainable without elevating simulated behaviour into a fraud finding. They also impose real engineering work: trusted manifest distribution, concrete schemas and ACLs, state-machine enforcement, mock execution, concurrent SQLite tests and adversarial/regression evidence must be delivered in **Part 2C**. The appropriate present judgement is **documented architectural coverage, subject to executable verification**, not a claim of implemented assurance or fraud-detection efficacy.

## 15. References and provenance

**Assessment and supplied design basis**

- [S1] *SWDA ML/AI Engineer Take-Home Assessment*, Part 2 and Annexes A/B (original assessment PDF; assessment-provided confidential exercise material).
- [S2] `P2_A1_Executive_Overview_v3.mmd`, `P2_A1_Simulation_Architecture_v3.mmd`, `P2_A1_Architecture_Notes_v3.md`.
- [S3] `P2_A2_Simulation_Sequence_v3.mmd`, `P2_A2_Sequence_Notes_v3.md`.
- [S4] `P2_A_Architecture_Verification_v3.md`, `P2_A_Static_Check_Results_v3.json`, `P2_A_Source_to_Render_Manifest_v3.json`.

**External engineering guidance (documentation, security and telemetry only; not sources of fraud evidence)**

- [E1] Microsoft, [Architecture design diagrams](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams), Azure Well-Architected Framework.
- [E2] Simon Brown, [C4 model](https://c4model.com/) and [dynamic/component views](https://c4model.com/diagrams).
- [E3] arc42, [Architecture documentation template](https://github.com/arc42/arc42-template).
- [E4] OWASP, [LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).
- [E5] NIST, [AI Risk Management Framework: Generative AI Profile (AI 600-1)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence), July 2024.
- [E6] OpenTelemetry, [Tracing API specification](https://opentelemetry.io/docs/specs/otel/trace/api/).

**Source-version qualification and independent review.** GitHub `I-c-e-m-a-n/SWDA_Test-Draft`, branch `main`, commit `e436f172233865d194df8334a6eb1adb51ad5ed8`, provides the canonical Part2A v3 `.mmd`, `.md` and JSON artefacts. Each of the eight local canonical source/report files matched its corresponding GitHub blob SHA on 6 November 2026. Separately suffixed notes/verification records were also recovered and matched the canonical files byte-for-byte; distinct suffixed Mermaid revisions were not located, so no equivalence to hypothetical different revisions is claimed. The Mermaid sources outrank notes, which outrank verification claims. **Open Part 2C decisions** are exact ACL and message/card schemas; independently protected source-manifest release provenance; local reviewer identity; the deterministic classification/abstention rule; treatment of failed or inconclusive CFs at the gate; and whether candidate-linked regression evidence is rerun or reused under a validated pinned version. These are not silently resolved. No Part 2A source or verification artefact was modified.
