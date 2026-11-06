# Executed remediation evaluation report

Verified during 6–7 November 2026, Asia/Singapore. Remediation baseline main:
`65c6f0d491aef2924bef74aa3668b43713740f2c`; reviewed implementation:
`e9e223b1c1ea3c84c734a619864dac58c4b1fb8d`. Python 3.12.14,
Pydantic 2.13.4, pytest 8.4.2. Source-code fingerprints, schema v2, scripts-2,
grounding registry version and policy/source snapshots are persisted in every valid run.

## Executed results

A previously absent environment was created with:

```bash
SWDA_VENV=/workspace/work/part2c-remediation/clean-venv ./Part2C/run.sh
```

The complete command installed locked dependencies and the editable package, ran pytest,
then executed all demonstrations and the independent evaluation. Result: **217 passed,
0 failures, 0 errors, 0 skipped**.
Pytest reported 24.09 seconds (one local observation, not a performance guarantee).
JUnit evidence: [pytest.xml](../examples/pytest.xml).

| Test module | Executed cases |
|---|---:|
| tests | 217 |

The 72-case baseline is preserved as its documented successor, with 145 additional cases.
The three legitimate expectation/fixture changes are explained in the remediation register.
No tests are skipped and no negative safety assertion was relaxed.

All **12 independent TEST fixtures passed**, consuming **41/60 calls**.
TEST runs created no children, decisions or review-queue entries.

| Fixture | Expected / actual | Result | Trace ID |
|---|---|---|---|
| valid_messages | COMPLETE / COMPLETE | PASS | `run-96ed2b912cb94658` |
| malformed_schema | BLOCKED / BLOCKED | PASS | `run-82abf14ecec94d52` |
| unauthorised_identity | BLOCKED / BLOCKED | PASS | `run-426e14f7046047cd` |
| forbidden_source | BLOCKED / BLOCKED | PASS | `run-388ee11c33c2406a` |
| reviewer_lookup | BLOCKED / BLOCKED | PASS | `run-df74d61294e34f40` |
| source_injection | COMPLETE / COMPLETE | PASS | `run-5548e6580407461b` |
| unsafe_unsupported | BLOCKED / BLOCKED | PASS | `run-21e878b343584bb8` |
| benign_s5 | NO_PATTERN / NO_PATTERN | PASS | `run-d93b277947d24e23` |
| single_actor | COMPLETE / COMPLETE | PASS | `run-b7c48d09c5824a9b` |
| two_actor_dependency | COMPLETE / COMPLETE | PASS | `run-6c5d40ef8f0f4e72` |
| three_role | COMPLETE / COMPLETE | PASS | `run-d5fa8340dfde4fd1` |
| timeout_budget | BLOCKED / BLOCKED | PASS | `run-5d36872150994fdc` |

Full reports and linked exports: [evaluation.json](../examples/evaluation.json) and
[evaluation-traces.json](../examples/evaluation-traces.json). These are deterministic control
fixtures, not independent empirical fraud labels or measured detection accuracy.

## Regenerated scenario evidence

| Scenario | Persisted outcome | Trace ID |
|---|---|---|
| two_actor | REVIEW_PENDING | `run-312cff93f0b146fb` |
| three_role | REVIEW_PENDING | `run-daa33ef5c2544dba` |
| single_actor | REVIEW_PENDING | `run-b42bbe86c961407d` |
| benign_s5 | NO_PATTERN | `run-4f4642c7b71b4926` |
| insufficient | NO_PATTERN | `run-9add07adf1334e46` |
| new_relative | NO_PATTERN | `run-e71f4dd9204b4f82` |
| variation | REVIEW_PENDING | `run-1eca35fbeaab4079` |

Each scenario has matching `.cards.json` and `.trace.json` files. All seven exports were
compared with fresh execution using the strengthened canonical representation and additional
card-field checks. All 12 evaluation traces were reconciled against fixture reports. The
previous positive new_relative card was replaced by an empty card list and an explicit
unsupported-mechanism trace. No sample carries a human approval.

## Verified controls and boundaries

Executed tests cover S5-only/unsupported concepts, independent feature partitions, two-/three-role
material cooperation, surviving smaller coalitions, forged/nonmaterial dependencies, fresh CF
contexts and descendant exclusion, reviewer input sensitivity and authority denial, relevant
investigation-data requirements, child-step annotation and root invalidation, invocation lifecycle,
rejected-output digests, post-execution timeout, interruption recovery, and denied-decision audits.
Concurrent human decisions and annotations admit at most one conflicting action. Forced insert
and deferred-FK COMMIT failures roll back state and success records; decision denial is recorded
separately. Audit-write failure returns an explicit failure. These use synthetic human identities,
not personal approvals by the repository owner.

Replay mutation tests cover classification, summary, contribution, flow, missing data, references,
CF verdict, reviewer objections, gates, evaluations, policy, pinned config, dependencies,
invocations and post-review human semantics. Fresh positive, negative and retry runs remain
canonical-equivalent. Exports are not mutated by canonicalisation.

Boundary tests exercise local calls 4/5, lineage calls 8/9, CF count 1/2, retries 0/2,
turns 11/12, four rounds, suite calls 40/41, fixture count 11/12, timeout before dispatch,
post-call timeout, card cap 1 and invalid limit configurations. Direct and concurrent CF
admission checks zero/full caps, duplicate removals, changed snapshots, invalid parents,
nonparticipation and exhausted allocation. Source tampering blocks before invocation.

Architecture checks verify exactly four scripts and rejection of an extra adapter, all 15
existing v3 manifest output digests, 14 sequence participants, six phases and 100 interactions.
No Part 1, Part 2A or Part 2B file was changed. Native Mermaid rendering was not executed.

## Reproduction

From a clean checkout:

```bash
./Part2C/run.sh
Part2C/.venv/bin/python -m pytest Part2C/tests -q
Part2C/.venv/bin/python -m swda_part2c.cli --db Part2C/runtime/recheck.db evaluate --output Part2C/runtime/recheck.json
Part2C/.venv/bin/python -m swda_part2c.cli --db Part2C/runtime/demo-recheck.db demo --output Part2C/runtime/demo-recheck
```

Remaining limitations: scripted authored assumptions, local OS identity, application-level
append-only SQLite, no hostile-Python sandbox, no preemption of a hung synchronous adapter,
and no real-model quality or real-world causality claims. NEW remains a comparator category;
no adequately grounded NEW scenario is demonstrated by the supplied annexes. See the
[remediation register](remediation_f1_f10.md) and [limitations](mock_model_limitations.md).
