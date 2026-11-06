# Release verification

Executed on 7 November 2026 (Asia/Singapore), Linux x86_64, Python 3.12.14.
Source: `I-c-e-m-a-n/SWDA_Test-Draft` main at `70c04fc27c35900fc1bdd0b54c675c5d6e8f29d8`.
Destination baseline: `e7684216aa35e1d39ebda4515c5cac14b6fa282e`.

## Scope and provenance

The destination branch preserves its own history. No source Git history was imported.
A separate clean clone at `/workspace/SWDA_verify` was created from the local migration
commit before installing either application. All application code, tests, configurations,
fixtures, locks, scripts, diagrams and the final PDF match the pinned source bytes.
Subsequent release changes add documentation and evidence only.

The [inventory](source-inventory.json) classifies all 129 source files: 118 KEEP,
7 REFINE and 4 EXCLUDE. Thus 125 source files were transferred, including seven refinements.
The empty destination `Readme.md` was replaced with `README.md`.
Excluded files are `Part2B/Test`, `Part1C/docs/pull_request.md` and the two AI-use narratives,
whose necessary disclosure is consolidated in the root README. Source inventory hashes
preserve their provenance. The source records support requirements and direction supplied
by the candidate, and AI implementation choices and executed checks; they do not establish
personal candidate verification.

The implementation decision document and F1–F10 register retain unique decisions,
security semantics and regression traceability, while obsolete branch/setup history and
changed-file lists are removed. The Part 2A historical verification and static JSON are
retained as architecture evidence, explicitly distinguished from this release run.
All sample cards, traces and historical JUnit remain unchanged because they substantiate
behaviour and participate in replay regressions.

## Executed checks

| Check | Current result |
|---|---|
| `./Part1C/setup.sh` | PASS; pinned binary wheels with hash verification; imports and pip check pass |
| `./Part1C/demo.sh` | PASS; actual SDK stdio discovery and tool invocation, protocol 2026-07-28 |
| `./Part1C/test.sh --junitxml=test-results.xml` | PASS; Ruff format/lint and 114 tests, no failures/errors/skips |
| `./Part2C/run.sh` | PASS; fresh dependency installation, 217 tests, no failures/errors/skips; seven scenarios, denied example and evaluation |
| Independent evaluation | 12/12 fixtures pass |
| Individual `run two_actor`, `pending`, standalone `evaluate` | Executed again against the local runtime database |
| Package imports | Exercised by setup, full suites and actual CLI/SDK execution |
| Shell syntax | All four retained shell entry points pass `bash -n` |
| Source/destination inventory | All retained files accounted for; 118 KEEP files byte-identical |
| Binary/image integrity | 21 PDF/PNG/SVG files byte-identical; SHA-256 recorded below |
| Part 2A manifest | All 15 packaged output sizes and hashes match; architecture regression passes |
| Documentation targets | 64 local Markdown targets resolved before adding this evidence report; final documentation checked again |
| Credentials | No private-key, GitHub token, AWS access-key or common API-key pattern matches in tracked files; heuristic scan only |
| Repository hygiene | Clean checkout remained clean after tests; generated runtime files ignored; whitespace check passes |

Fresh [Part 1C JUnit](verification/part1c-junit.xml), [Part 2C JUnit](verification/part2c-junit.xml),
[evaluation](verification/part2c-evaluation.json), [scenario outcomes](verification/part2c-scenarios.json)
and [integrity hashes](verification/integrity.json) record this execution. UUIDs in these
reports refer to this run, not the retained historical examples. Full fresh runtime traces
remain local and can be regenerated with `./Part2C/run.sh`.

Part 1C's full suite exercises policy digest/schema bindings, classification/catalogue
semantics, fresh discovery/call approval, and real loopback HTTP transport. Part 2C's
full suite includes all remediation regressions for source integrity, four role-bound
adapters, source/recipient ACLs, counterfactual admission and shared budgets, unsafe output,
human-only approval, transactional persistence and trace replay. No test assertions,
security gates or trusted digests were changed.

## Limitations and release status

All six deliverable sections are present. Historical v2 manifest inputs (12 entries) and
historical offline generator/verifier scripts were not included in the source repository;
they cannot be independently reconstructed from this release. All 15 retained v3 output
entries are verified. Native Mermaid rendering, native macOS execution, remote CI,
enterprise integrations and real-model quality were not verified in this release run.
SVG XML and PNG signatures were checked in addition to exact source-byte comparison.

No simulated candidate was approved by migration automation. Human approval behaviour is
covered by synthetic tests; candidate personal review and technical-defence readiness
remain the candidate's responsibility. GitHub publication and pull-request status are
reported separately at delivery, not inferred from local test success.
