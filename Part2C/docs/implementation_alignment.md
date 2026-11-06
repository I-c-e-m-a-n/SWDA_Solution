# Executable alignment to Part 2A v3 and Part 2B v2

Baseline remote main: `2c49c4a9840bf42a62182ae0deaf7939014c5ccd`.
The initial local HEAD was `020b6883f1ba319303886153aca1080d9e07551c`; after enabling
network access, the implementation branch fast-forwarded to the inspected baseline.
No baseline Part 1, Part 2A or Part 2B file is changed by this implementation.
All ten text artifacts in Part2A/B were read, including the whitespace-only `Part2B/Test`.
Mermaid sources define the architecture; existing render/verification claims establish no runtime result.

| Part 2A A1 | Part 2A A2 | Executable component |
|---|---|---|
| OUT / IN | POL | `policy.Gateway.dispatch`, `.receipt`, `.lookup`: one gateway |
| CARD / DEP | ANA | `analysis` assembler/graph helpers; bounded CF scheduling in ORCH |
| GATE | SAFE | `safety.assess`, strict parsing and fail-closed exception paths |
| APPROVAL | APPR | `approval.ApprovalService`: configured OS user, transaction and CAS |
| STATE / EVENTS / TRACE / DECISION | STORE | `store.Store`, relational runs, records, budgets, decisions, annotations |
| LOAD / CAT / MO / REF | CAT and trusted helpers | `sources.Catalogue`, `release.EXPECTED`, `analysis.compare`; REV reads through POL |
| INIT / ORCH / CTX | ORCH | `orchestrator.Orchestrator.execute`, isolated invocation Context |
| TA / PA / EA / REV | Same actors | Three role-bound ScriptedActor instances and ScriptedReviewer |
| EVAL / FIX | EVAL | `evaluation.evaluate`, twelve independent top-level TEST fixtures |
| UI / DEC | CLI | `cli` full history, record inspection, step annotation and interactive human decision |

## Six execution phases

1. **Initiation/source trust:** CLI chooses versioned scenario; ORCH persists an unapproved run,
   verifies exact annex bytes against independently pinned release literals, freezes source/ACL/
   limits/seed/schema/adapter snapshots, then dispatches. Corrupt input blocks before invocation.
2. **Bounded simulation:** ORCH schedules role-specific contexts. Dispatch and receipts validate
   identity, purpose, recipients, source scope, ancestry and typed output. Repair consumes shared
   budgets and preserves envelope scope. Model operations cannot change policy or run type.
3. **Pattern/dependency analysis:** validated messages contribute abstract features, claims and
   benefits. Cards reflect actual material contributors. Each contributor gets an independent CF
   with fresh IDs/adapters/history, pinned source/policy/seed and shared lineage budget. No parent
   message is copied, so removed contributions and descendants cannot leak. Independent survivor
   behaviour can be regenerated from the annex baseline. Failed/inconclusive CF blocks release.
4. **Machine review/assurance:** REV receives a structured contribution draft and requests exact
   reference IDs/purpose. Gateway filters returns; trusted comparator provides reproducible feature
   matching. REV recommends only. Independent safety code revalidates provenance, quotes,
   policy receipts, budgets, CF completion, review and candidate-linked evaluation. Only passing
   CANDIDATE enters REVIEW_PENDING. TEST assembly has no human eligibility.
5. **Human-only action:** terminal captures deliberate human action/rationale. Approval revalidates
   local role, persisted passing gate set, current state and version in BEGIN IMMEDIATE. Status,
   decision and audit row commit together. Tests force concurrent conflicts and COMMIT failure.
6. **Independent evaluation/observability:** twelve top-level TEST fixtures use the same ORCH/POL,
   with local/suite caps and no derivation or decision service. JSON report links complete exported
   traces. Approval tests run separately on synthetic CANDIDATE databases.

## Deliberate implementation choices and limits

The diagrams leave schema/ACL values, local identity, classification thresholds and inconclusive-CF
release semantics open. Resolutions were recorded before implementation in `preimplementation.md`.
There is one card per supported scenario (within the maximum three), two default simulation rounds,
and three candidate actors at most. Reviewer invocation also consumes the actor-turn budget, a
conservative interpretation. Default scripts therefore use at most seven turns per three-role run.
A single-role candidate is separately labelled by its contribution/CF finding, without calling it collusion.

The authoritative design asks for isolation but does not mandate process-level hostile-code execution.
The PoC supplies no ambient service handles to scripts; it does not claim OS sandboxing. Elapsed-time
checks cannot forcibly cancel arbitrary synchronous Python. These limitations are explicit rather than
claimed as fully tested production controls. Native Mermaid rendering has not been rerun; this task
adds runtime evidence without modifying or re-certifying Part 2A's derivatives.

## F1–F10 remediation against current main

Remediation starts from `65c6f0d491aef2924bef74aa3668b43713740f2c` (the merge of
reviewed `e9e223b1c1ea3c84c734a619864dac58c4b1fb8d`). Part 1, Part 2A and
Part 2B are unchanged. All four scripted adapters and six phases remain.

| Phase | Strengthened executable responsibility |
|---|---|
| 1 | `grounding.support` checks all configured risk features, independent of mode; snapshot pins registry/code/schema/scripts. |
| 2 | Gateway checks explicit material dependencies and source support; `Store.consume` atomically records invocation start and usage. |
| 3 | `dependency_graph` distinguishes coverage from cooperation; `cf_outcome` identifies surviving coalitions. `Store.create_run` atomically admits CFs against persisted caps and reservations. `assemble` emits trace-linked directed flows. |
| 4 | `review.review` examines the full draft; `safety.assess` independently rebuilds it and validates findings and empirical data. |
| 5 | `ApprovalService.annotate` resolves child ownership and invalidates the root atomically; `decide` audits denials after rollback. Historical approvals are preserved. |
| 6 | Versioned canonical forms preserve simulation and post-review semantics; regression modules cover all ten findings and the independent boundary probes. |

These are refinements within the existing logical components, not new agents or services.
SURVIVING_COALITION refines the design's coarse CF outcome vocabulary; no diagram is
rewritten. Schema v2 explicitly records required dependency features and flow endpoints.
Unsupported hypotheses abstain; inconclusive dependency/review findings remain blocked.
Native Mermaid rendering remains outside this patch's executed verification.
