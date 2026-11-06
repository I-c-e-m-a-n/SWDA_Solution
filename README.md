# SWDA ML/AI Engineer Take-Home Assessment

**MLOps, AIOps and MCP-enabled Agent Delivery**

## Executive Overview

This submission combines an enterprise architecture proposal with two executable Python proofs of concept. Part 1 demonstrates governed MCP discovery and deterministic service recommendations. Part 2 demonstrates controlled interaction between four mock agents, evidence-bounded risk hypotheses and a separate human decision service. Both implementations use synthetic data. Neither is a deployed SWDA service.

The release preserves implementation, test assertions, source fixtures, permissions and approval semantics from source commit `70c04fc27c35900fc1bdd0b54c675c5d6e8f29d8`. See the [file inventory](docs/source-inventory.json) and [release verification](docs/release-verification.md) for transfer decisions and current execution evidence.

## Assessment Objectives and Scope

Part 1 addresses enterprise MLOps, agent registration, approval and MCP access governance. The local implementation exercises one bounded service recommendation tool. Part 2 addresses annex-restricted multi-agent simulation, governed communication, comparison with illustrative reference patterns, counterfactual analysis, evaluation and human oversight.

Architecture documents describe production responsibilities beyond the local implementations. Cloud identity, enterprise gateways, production deployment, real-model quality and real-world risk detection are not demonstrated by these proofs of concept. Approval in Part 2 permits further investigation only; it is never a finding of wrongdoing.

## Repository Structure and Deliverables

| Section | Authoritative artefacts |
|---|---|
| Part 1A | [Architecture notes](Part1A/architecture_notes.md), [assumptions](Part1A/assumptions_register.md), [four editable diagrams and SVG/PNG exports](Part1A/diagrams/) |
| Part 1B | [Final design PDF](Part1B/SWDA_Part1B_Design_Document_Final.pdf) |
| Part 1C | [Implementation and operating guide](Part1C/README.md), [source](Part1C/src/), [tests](Part1C/tests/), [synthetic catalogue](Part1C/data/synthetic_programmes.json), [approval fixture](Part1C/policy/approved_agent.json) |
| Part 2A | [Executive architecture](Part2A/P2_A1_Executive_Overview_v3.svg), [detailed architecture](Part2A/P2_A1_Simulation_Architecture_v3.svg), [sequence](Part2A/P2_A2_Simulation_Sequence_v3.svg), [sources and six phase images](Part2A/), [architecture notes](Part2A/P2_A1_Architecture_Notes_v3.md), [sequence notes](Part2A/P2_A2_Sequence_Notes_v3.md), [render manifest](Part2A/P2_A_Source_to_Render_Manifest_v3.json) |
| Part 2B | [Final v2 design note](Part2B/P2_B_Design_Note_v2.md) |
| Part 2C | [Implementation and operating guide](Part2C/README.md), [source](Part2C/src/), [tests](Part2C/tests/), [configuration](Part2C/config/), [annex fixtures](Part2C/data/), [sample outputs](Part2C/examples/) |

Each coding section retains its dependency lock and scripts. The Part 2A manifest retains historical v2 input provenance as well as 15 packaged v3 outputs. The historical inputs were absent from the supplied source tree; they are not missing migration outputs.

## Part 1: Enterprise MLOps and Governed MCP Architecture

The four Part 1A diagrams cover enterprise AI architecture (A1), the MLOps lifecycle (A2), agent registry approval (A3) and MCP runtime sequence (A4). The design separates development and release responsibilities from runtime access. Registry state, versioned artefacts, identity, policy and observability form distinct controls. The [design PDF](Part1B/SWDA_Part1B_Design_Document_Final.pdf) and [assumptions register](Part1A/assumptions_register.md) define scope and external dependencies.

The local agent simulates publication and approval with a version-controlled fixture. It does not deploy the proposed enterprise registry, Databricks integration or independent approval authority. [Architecture alignment](Part1C/docs/architecture_alignment.md) distinguishes implemented, simulated and unverified capabilities.

## Part 1C: Service Recommendation Agent

A real MCP SDK server exposes only `recommend_service`. Discovery and each invocation check current policy. Strict request validation precedes deterministic classification and bounded catalogue lookup. The response includes advisory status, reason codes and artefact versions; audit metadata goes to stderr, leaving stdout for MCP transport.

Classification counts distinct keywords for employment, skills and care. A unique highest score selects a category; ties request human review and unknown requests abstain. Catalogue lookup filters active entries by category and channel, sorts by priority and identifier, and returns at most three programmes. It performs no eligibility assessment and calls no LLM.

The synthetic policy requires PUBLISHED state, matching release and tool-schema digests, permitted scope and an unexpired approval. Discovery cannot bypass call-time checks. Code, dependency lock and catalogue remain byte-identical to the source release. The fixture expires on 6 November 2027 at 00:00 UTC. It is not a signed production attestation.

The demo uses actual SDK stdio discovery and invocation. Loopback HTTP integration is covered by the test suite. The [operating guide](Part1C/README.md) documents optional HTTP startup, strict contracts, error categories and bounded resources.

## Part 2: Controlled Multi-Agent Risk Simulation

Exactly four role-bound scripted adapters participate: TA, PA, EA and REV. The deterministic orchestrator, gateway, comparator, safety gates and persistence layer are ordinary application code. A shared gateway checks sender, recipient, source access and operation permissions on dispatch and receipt. REV has narrowly scoped reference access; role boundaries are not broadened for convenience.

Annex A/B fixtures are the only simulation sources. Trusted release digests verify source integrity. Direct illustrative MO support is required for risk features; weak context or benign S5 material cannot establish wrongdoing. Closed output contracts and independent safety checks block unsupported claims and unsafe outputs.

The orchestrator builds material dependency graphs and runs fresh actor-removal counterfactuals. Parent messages are not copied into child contexts. Persisted admission checks and shared budgets constrain calls, retries and child runs. Comparison yields KNOWN, VARIATION or NEW relative to illustrative signatures, not empirical novelty. No supplied scenario supports a review-eligible NEW mechanism.

See [Part 2B](Part2B/P2_B_Design_Note_v2.md), [implementation decisions](Part2C/docs/preimplementation.md), [requirements traceability](Part2C/docs/requirements_traceability.md) and [control regression mapping](Part2C/docs/remediation_f1_f10.md).

## Part 2C: Implementation and Human Approval Workflow

A candidate progresses through simulation, grounded analysis, counterfactual checks, deterministic review and safety gates. Eligible cards enter REVIEW_PENDING. Benign or unsupported scenarios produce NO_PATTERN; denied operations are blocked. SQLite retains runs, lineage, invocation outcomes, gate results and append-only trace and decision records.

Simulated agents receive no approval-service handle. TEST and CF runs cannot approve candidates. A separate terminal workflow verifies the current OS user against a local reviewer allowlist, requires a substantive rationale and explicit confirmation, and rechecks candidate state, version and persisted gates in a transaction. Conflicting decisions cannot both commit. Step rejection or dispute invalidates affected pending or approved work without rewriting historical messages.

The committed reviewer list is empty. Only an authorised human operator should configure their own local reviewer file and record a decision. From the repository root after setup:

```bash
PY=Part2C/.venv/bin/python
$PY -m swda_part2c.cli pending
$PY -m swda_part2c.cli history RUN_ID
$PY -m swda_part2c.cli inspect RUN_ID STEP_ID
```

For an authorised local operator, create the ignored configuration:

```bash
mkdir -p Part2C/runtime
python3 - <<'PY'
import getpass, json
from pathlib import Path
Path('Part2C/runtime/reviewers.json').write_text(json.dumps({
    'version': 'local-1', 'reviewers': [getpass.getuser()]
}))
PY
```

Inspect the run, then record a deliberate human decision. Replace RUN_ID and VERSION with the current candidate ID and version:

```bash
$PY -m swda_part2c.cli --reviewers Part2C/runtime/reviewers.json review RUN_ID
$PY -m swda_part2c.cli --reviewers Part2C/runtime/reviewers.json decide RUN_ID APPROVE_FOR_INVESTIGATION --version VERSION --rationale 'Describe the actual investigation justification here.'
```

These are alternative interactive paths, not two decisions to execute in sequence. `decide` requires typing the exact action; `review` requires `COMMIT`. Other actions are `REJECT` and `REQUEST_REVISION`. No migration automation grants a human approval. See the [Part 2C guide](Part2C/README.md) for annotations, export and recovery.

## System Requirements and Environment Setup

Use Python 3.12 with venv and pip, Bash and Git. Both packages use separate virtual environments because their dependency versions differ. First installation requires access to PyPI and its file host. Tests and demonstrations use local synthetic data without API keys, cloud credentials, Docker or model downloads.

Part 1C requires exactly Python 3.12 and installs binary wheels with pinned hashes. Set `PYTHON_BIN` if needed. Part 2C uses `python3` and supports Python 3.12 or newer; use Python 3.12 for the verified workflow. Its lock pins versions but does not provide the same hash enforcement as Part 1C. Do not disable TLS or integrity checks to resolve installation failures.

The required environment supports subprocesses, stdio and loopback sockets. Part 1C documents macOS 15 support; current release execution and any unverified platform claims are distinguished in the release report. Generated databases and fresh outputs remain in ignored runtime directories. Retained examples are historical evidence, not new execution results.

## Quick Start and Demonstration Commands

From the repository root:

```bash
./Part1C/setup.sh
./Part1C/demo.sh
./Part1C/test.sh --junitxml=test-results.xml
./Part2C/run.sh
```

Part 2C's one-command script installs dependencies and the package, runs the full tests, executes seven scenarios and a denied-operation example, and evaluates 12 independent fixtures. To inspect or rerun individual operations:

```bash
PY=Part2C/.venv/bin/python
$PY -m swda_part2c.cli scenarios
$PY -m swda_part2c.cli run two_actor
$PY -m swda_part2c.cli run three_role
$PY -m swda_part2c.cli run single_actor
$PY -m swda_part2c.cli run benign_s5
$PY -m swda_part2c.cli run insufficient
$PY -m swda_part2c.cli run new_relative
$PY -m swda_part2c.cli run variation
$PY -m swda_part2c.cli evaluate --output Part2C/runtime/evaluation.json
$PY -m pytest Part2C/tests -q
```

`two_actor`, `three_role`, `single_actor` and `variation` should enter REVIEW_PENDING. `benign_s5`, `insufficient` and `new_relative` should return NO_PATTERN. Evaluation runs TEST fixtures and does not approve candidates. Global `--db PATH` and `--reviewers PATH` options precede the subcommand.

## Testing, Evaluation and Verification Evidence

[Release verification](docs/release-verification.md) records current clean-checkout results, binary comparisons and limitations. [Source inventory](docs/source-inventory.json) classifies every tracked source file. Source code, executable tests, locks, policy, configuration, fixtures, binary documents and diagrams are preserved without behavioural edits.

Part 1C tests cover classification, catalogue ordering, schemas, registry transitions, fresh approval, tampering, SDK stdio and HTTP transports, sanitized errors and limits. Part 2C tests cover source integrity, role permissions, governed messages, semantic review, counterfactual admission, shared budgets, persistence failures, human-only approval, concurrency and replay. All `test_remediation_*` files are retained.

[Part 1C historical evidence](Part1C/docs/test_evidence.md) and [Part 2C historical evaluation](Part2C/docs/evaluation_report.md) describe earlier runs. [Sample traces, cards, evaluation and JUnit](Part2C/examples/) remain unchanged for replay regression. GitHub Actions checks are included for [Part 1C](.github/workflows/part1c.yml) and [Part 2C](.github/workflows/part2c.yml); local success does not establish remote CI success.

## Security, Governance and Operational Limitations

These are deterministic proofs of concept. Keyword routing does not understand intent reliably. Scripted simulation does not measure real-model quality, causality or fraud detection. Synthetic hypotheses are not findings about real people or organisations.

In-process capability separation is not a hostile-code sandbox. Synchronous time checks cannot preempt arbitrary hung adapters. SQLite append-only controls are not tamper-proof against a privileged host operator. Local OS identity is not enterprise IAM or MFA. The optional MCP HTTP endpoint is loopback-only and must not be publicly exposed. Production authentication, independent attestations, durable external audit and enterprise gateway interoperability require separate implementation and validation.

Native Mermaid rendering was not established by the source evidence. The retained diagrams include offline source-derived renderings. Historical manifest input files and generator scripts were not packaged in the source; output hashes and architecture regressions can be checked independently. See [Part 1 limitations](Part1C/docs/security_limitations.md) and [Part 2 limitations](Part2C/docs/mock_model_limitations.md).

## AI Assistance

The candidate supplied the assessment requirements and directed the implementation and release objectives. AI assisted with research, implementation and verification material.

**Prompt:** The candidate provided detailed requirements, constraints and expected results.

**Response:** AI provided technical information, proposed implementation choices, code, tests and documentation.

**Application:** The candidate directed how the material was used to meet the assessment requirements. AI executed the recorded automated checks. The candidate remains responsible for understanding and defending the submission; personal review and verification are not asserted here.
