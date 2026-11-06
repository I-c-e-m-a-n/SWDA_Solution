# Part 2C — Controlled multi-agent risk simulation

A runnable, annex-only Python 3.12 proof of concept. Exactly four scripted mock agents
(TA, PA, EA and REV) operate under a deterministic orchestrator. Outputs are hypothetical
risk patterns, never findings about actual people, providers, employers or grant claims.
Approval permits further investigation only.

## Run everything

From the repository root:

```bash
./Part2C/run.sh
```

This creates `Part2C/.venv`, installs the exact versions in `requirements.lock`, runs pytest,
executes seven deterministic scenarios and one denied-operation example, then runs the
12-fixture independent evaluation suite. First installation needs PyPI access; tests and
simulation require no network afterwards. Python 3.12+ with `venv` and pip is required.
Set `SWDA_VENV=/absolute/path` for another environment. No setup/demo command approves a candidate.

Runtime SQLite, JUnit evidence and generated JSON live in ignored `Part2C/runtime/`.
Committed, executed examples are in [examples](examples/). IDs and timestamps vary;
`analysis.canonical` compares semantic replay outputs.

## Commands

From the repository root, use this interpreter after setup:

```bash
PY=Part2C/.venv/bin/python
$PY -m pytest Part2C/tests -q
$PY -m swda_part2c.cli scenarios
$PY -m swda_part2c.cli run two_actor
$PY -m swda_part2c.cli pending
$PY -m swda_part2c.cli history RUN_ID
$PY -m swda_part2c.cli inspect RUN_ID STEP_ID
$PY -m swda_part2c.cli review RUN_ID
$PY -m swda_part2c.cli annotate STEP_RUN_ID STEP_ID REJECTED --candidate RUN_ID --version 1 --rationale 'The modelling premise needs independent revision.'
$PY -m swda_part2c.cli decide RUN_ID REQUEST_REVISION --version 1 --rationale 'Independent corroboration is needed before further consideration.'
$PY -m swda_part2c.cli evaluate --output Part2C/runtime/evaluation.json
$PY -m swda_part2c.cli export RUN_ID --output Part2C/runtime/export.json
$PY -m swda_part2c.cli recover
```

Replace RUN_ID and STEP_ID with values from `pending`/`history`. An individual record's
`id` identifies messages, invocations, gates, decisions and audit events. History contains
ordered records, invocation contexts and outcomes (rejected outputs are digested), dispatch/receipt decisions, sources,
retry scopes, usage counters, CF children, cards, review recommendations, gates and human history.
Every record has a trusted sequence number and timestamp. Export preserves the same overview.
`recover` marks abandoned RUNNING executions INCOMPLETE. Use it only after the active operator
has stopped execution; this local PoC has no distributed worker leases.

Global options precede the subcommand: `--db PATH` and `--reviewers PATH`. The default database
is `Part2C/runtime/runs.db`. A separate database can isolate an experiment.

### Human identity and oversight

The committed reviewer list is empty. A human operator must configure their local OS username
in a private local configuration file, for example:

```bash
mkdir -p Part2C/runtime
python3 - <<'PY'
import getpass, json
from pathlib import Path
Path('Part2C/runtime/reviewers.json').write_text(json.dumps({'version':'local-1','reviewers':[getpass.getuser()]}))
PY
$PY -m swda_part2c.cli --reviewers Part2C/runtime/reviewers.json review RUN_ID
```

This is a configured local role checked against the current OS user. It is **not enterprise IAM**,
MFA or an identity boundary against someone controlling that OS account or application code.
The CLI requires a deliberate terminal action and rationale. `decide` asks the human to type
the exact action; interactive `review` asks for `COMMIT`. There is no noninteractive approval flag.
The three actions and persisted states are:

| Human action | Persisted state |
|---|---|
| APPROVE_FOR_INVESTIGATION | APPROVED_FOR_INVESTIGATION |
| REJECT | REJECTED |
| REQUEST_REVISION | REVISION_REQUESTED |

The service rechecks CANDIDATE, REVIEW_PENDING, expected version, all persisted gates, the local
human role and substantive rationale inside a SQLite transaction. At most one conflicting decision
commits. A receipt is returned only after COMMIT. TEST/CF and model-origin requests cannot approve.

Step annotations are separate, append-only oversight records. Use the actual candidate or child CF run ID as STEP_RUN_ID; history includes child records. The service resolves the candidate from persisted lineage and checks the supplied candidate ID and version. Every accepted annotation increments the candidate version; stale or duplicate annotations are denied. ACCEPTED does not approve a card.
REJECTED and DISPUTED require reasons and move pending/previously approved work to
REVISION_REQUESTED; the original messages and decision history remain visible. All recorded
material simulation steps are treated conservatively as affecting the single card. A revision
requires a new operator-selected run; no automatic rerun or gate bypass exists.

## Expected scenarios

| Scenario | Expected outcome |
|---|---|
| two_actor | PA→TA exchange; KNOWN relative to MO-04; two fresh CFs; REVIEW_PENDING |
| three_role | PA→EA→TA exchange; VARIATION of MO-06/MO-08; three fresh CFs; REVIEW_PENDING |
| single_actor | TA-only hypothesis relative to MO-03; single-actor finding; REVIEW_PENDING |
| benign_s5 | Explicit NO_PATTERN; no card or approval queue entry |
| insufficient | Explicit NO_PATTERN for S1/S2/S4 without attributable contributions |
| new_relative | NO_PATTERN: S1/S2 provide weak context, insufficient to support a misconduct mechanism |
| variation | Partial MO-04 feature match; REVIEW_PENDING |

The feature mapping is a documented modelling assumption. It cannot establish empirical novelty.
Fault behaviours are invoked by trusted tests, not by model output: malformed, repair, sender,
recipient, source, operation, unsafe, unsupported, reviewer_lookup and reviewer_invalid.
The injection fixture is a separately pinned TEST-only perturbation of S3; the original annex
fixture is preserved byte-for-byte at its release version. Injection text is inert attributed data.

## Architecture and evidence

* `schemas.py`: strict immutable Pydantic v2 contracts.
* `sources.py` + `release.py`: immutable catalogue, SHA-256 against release-owned expected hashes.
* `config/`: versioned scenario, role ACL, limit and reviewer configuration.
* `policy.py`: one gateway for dispatch, receipt and narrowly authorised reviewer reference reads.
* `models.py`: shared adapter interface and four independently configured scripts.
* `orchestrator.py`: finite scheduler, unchanged retry scopes, fresh CF state and shared budgets.
* `grounding.py`: versioned Annex concept support and relevant investigation-data categories.
* `review.py`: substantive deterministic review rules, independently recomputed by safety gates.
* `analysis.py`: material dependency graph, directed flows, comparator, evaluation and versioned semantic replay.
* `safety.py`: deterministic gates independent of generated recommendations.
* `store.py`: SQLite runs, lineage, records, budgets and append-only trace tables.
* `approval.py`: local human role, annotations and atomic compare-and-swap decisions.
* `evaluation.py` + `cli.py`: independent TEST suite and terminal oversight.

Read [alignment](docs/implementation_alignment.md), [traceability](docs/requirements_traceability.md),
[decisions made before implementation](docs/preimplementation.md), [executed evaluation](docs/evaluation_report.md),
[limitations](docs/mock_model_limitations.md) and [AI declaration](../README.md#ai-assistance).

## Trust limits

The agents receive immutable data objects and no database, filesystem, network or approval
service handles. This is capability separation for supplied scripts inside one Python process,
not a hostile-code sandbox. A future untrusted Python adapter needs a separate process/container
and a bounded cancellable protocol. Current mock elapsed-time checks stop before/after each
synchronous operation; they cannot preempt a hung arbitrary adapter.

Closed output grammar, exact source quotation checks, fixed tools, ACLs and deterministic gates
prevent the tested unsafe outputs. They are intentionally restrictive, not a general natural-language
safety classifier. Scripted review inspects contributions, provenance, assumptions, references and CF objections; it does not
prove independent human-quality reasoning. Annexe excerpts and source identifiers are attribution,
not proof of misconduct. Joint compromise of trusted release hashes and data defeats digest checks.
SQLite triggers provide application append-only records, not cryptographic tamper-proof storage
against privileged OS users. Source and release review are the operator's responsibility.

## Remediation contract (1.1.0)

See [F1–F10 corrections and regressions](docs/remediation_f1_f10.md). Every risk feature
requires direct illustrative MO support; excerpt context never establishes wrongdoing.
S5-only and unsupported mechanisms return NO_PATTERN before model calls. No unsupported
feature is silently discarded. NEW remains a comparator category, but no supplied
annex-only scenario currently substantiates a review-eligible NEW mechanism.

Dependencies identify earlier authorised material messages and the precise features consumed.
Feature coverage and message succession alone cannot establish cooperation. Surviving
smaller coalitions are distinguished from single-actor feasibility; inconclusive CFs block.
CF admission atomically enforces persisted limits, unique removed roles, pinned settings
and call reservations. Human decisions remain investigation-only.

Each consumed call atomically records its start and usage, then its terminal result.
Rejected payloads retain hashes, sizes and reason codes; they are never delivered.
Decision failures roll back before a separate denial audit; audit-write failure is explicit.
`canonical(export)` describes the simulation; `canonical(export, post_review=True)` also
includes human decisions and annotations. Both preserve semantic evidence and normalise
generated identities and clocks. They do not establish cryptographic audit integrity.
