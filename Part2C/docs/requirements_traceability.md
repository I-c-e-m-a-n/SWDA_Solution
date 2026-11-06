# Requirements-to-implementation traceability

Authority: original assessment Part 2 and Annexes A/B, read through the supplied Drive PDF.
Architecture: Part2A v3 Mermaid; explanations: Part2A notes and Part2B v2.
The ten rows below preserve the assessment's actual requirement grouping.
Paths are relative to Part2C; examples are executed artifacts, not evidence of real misconduct.

| # | Assessment requirement | Implementation/config | Executable verification | Sample evidence |
|---|---|---|---|---|
| 1 | Actor profiles with distinct goals, capabilities, visible information | `schemas.Profile`, `models.py`, `config/profiles.json`, scoped Context | `test_dispatch_denied_without_source_return`, `test_routing_ancestry_and_fresh_cf` | `examples/two_actor.trace.json` invocation contexts |
| 2 | Controlled actor-to-actor messages | `orchestrator.py`, `policy.Gateway`, immutable Envelope | `test_full_workflows`, `test_routing_ancestry_and_fresh_cf` | two_actor PA→TA and three_role PA→EA→TA traces |
| 3 | Code-enforced least privilege | source/recipient/purpose ACLs, exact bound receipts, no injected service handles | `test_adversarial_fail_closed`, `test_review_lookup_filters_and_denies` | `examples/denied.trace.json`; evaluation denied identity/source/lookup |
| 4 | Actors, contributions, benefits and flows in cards | `analysis.assemble`, typed Card/Claim/Contribution | `test_full_workflows` | `examples/two_actor.cards.json`, `three_role.cards.json` |
| 5 | Actor removal and single-actor separation | fresh CF contexts, contribution features/ancestry, depth-one lineage, conservative gates | `test_three_role_removal_never_assumes_single`, `test_failed_counterfactual_blocks_release`, `test_inconclusive_surviving_two_roles_blocks_candidate` | linked CF children; `single_actor.cards.json` |
| 6 | Source/simulation/assumption separation | `sources.py`, release hashes, labelled assertions; preserved original annex fixture | `test_annex_integrity_exact_ids_and_control`, tamper/injection/replay tests | SOURCE/SIMULATION/ASSUMPTION card assertions and source manifest snapshots |
| 7 | Known/variation/new and required testing data | explicit feature signatures in `analysis.compare`, less-trusted REV via gateway | `test_pre_adjudicated_classification`, all seven workflows | known/variation cards with weak confidence and relevant data; unsupported NEW abstains |
| 8 | Schemas, retries, round/cost limits | strict frozen schemas, pre-call local/lineage/suite quotas, retry scope, elapsed checks | repair/boundary/suite-budget/oversized tests | invocation attempts and usage scopes in traces; evaluation report |
| 9 | Hidden-instruction/unsafe-output safeguards and human approval | closed actor output grammar, exact quotes, `safety.py`, `approval.py`, interactive CLI | injection/unsafe tests; all approval integration tests, forced rollback/commit failure | denied trace, pending candidate; JUnit synthetic human decisions |
| 10 | Traces, agent/E2E evaluation, regression | SQLite ordered timestamped records, exports, canonical replay, 12-fixture independent suite | full pytest suite; `test_test_suite_is_independent_and_bounded`, replay/recovery/append-only tests | `examples/evaluation.json`, `evaluation-traces.json`, `pytest.xml` |

## Additional master-prompt contracts

| Contract | Evidence |
|---|---|
| Exactly four mock agents, ORCH is deterministic | `models.adapters`, exact adapter-key check; all workflows |
| Expected digest independent of source input | release literals; altered/missing source fail before invocation |
| CF/TEST cannot recurse or enter approval queue | Run validation and candidate-parent check; TEST/CF approval denial tests |
| Budgets never replenish on repair or derivation | atomic Store.consume across scopes; lineage/suite exhaustion tests |
| Human origin, expected version, no misleading receipt | role/origin tests, stale/duplicate/concurrency and actual COMMIT failure tests |
| Rejected step does not rewrite trace | separate annotations table; equality of messages before/after rejection |
| No automatic demo approvals | `cli.demo` has no ApprovalService call; empty committed reviewer list |
| Replay/recovery | canonical semantic comparison, explicit abandoned-run recovery |
| Full runnable repository and clean one-command path | run.sh; clean-environment execution recorded in evaluation report |

The signed/trusted-release distribution process, enterprise identity, general model safety and realistic
collusion reasoning are not proved by these fixtures. See `mock_model_limitations.md`.

## Remediation evidence by assessment requirement

| Requirement | Additional executable evidence |
|---|---|
| 1–3 | `test_remediation_architecture` checks exactly four scripts and rejects an extra adapter; existing routing/ACL tests retained. |
| 4 | F10 tests verify distinct mechanisms, actor contributions, directed flows and actual trace references. |
| 5 | F2 tests cover independent partitions, two-/three-role cooperation, smaller surviving coalitions, invalid dependencies and final-contribution ancestry. |
| 6 | F1 tests distinguish illustrative risk support, weak context, benign evidence and unrelated source citations. |
| 7 | F3/F4 tests alter reviewer inputs and test empty, irrelevant and duplicate investigation-data requirements. Unsupported NEW returns NO_PATTERN. |
| 8 | F6/F9 and boundary tests exercise invocation accounting, direct/concurrent CF admission and all configured caps. |
| 9 | F5/F7 tests cover child-step oversight, stale/concurrent actions, denial audit and forced insert/COMMIT failures. |
| 10 | F8 mutation/replay checks, sample reconciliation, 12 isolated evaluation fixtures and clean setup evidence. |

Full correction mapping and legitimate baseline expectation changes: [remediation register](remediation_f1_f10.md).
