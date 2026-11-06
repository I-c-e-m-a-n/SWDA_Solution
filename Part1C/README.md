# Part 1C — Governed MCP Service Recommendation Agent

A runnable **synthetic local demonstration**, not an official SWDA service or eligibility
decision. Uses official MCP Python SDK **2.3.0**, `MCPServer`, `Client`, and revision
**2026-07-28**. No LLM, API keys, cloud login, Docker, database, or model downloads.

## Run on macOS (Apple Silicon or Intel)

The supported target is macOS 15 or newer; older releases are not verified.

Install Python **3.12** using the universal2 installer from
[python.org](https://www.python.org/downloads/macos/) if it is not already available.
The scripts require only Bash 3.2, Python's venv and pip; no Homebrew or sudo.

```bash
git clone https://github.com/I-c-e-m-a-n/SWDA_Solution.git
cd SWDA_Solution/Part1C
./setup.sh
./demo.sh
./test.sh
```


For a nonstandard Python location: `PYTHON_BIN="/path with spaces/python3.12" ./setup.sh`.
All scripts resolve their own directory and quote paths, including repositories in folders
with spaces. Python 3.12 is checked before creating or using `.venv`. No system packages
are installed. Activate `.venv` only if desired; scripts use it explicitly.

`setup.sh` installs exact transitive pins using pip `--require-hashes --only-binary=:all:`, checks dependency
consistency and imports. Run it again safely to verify/refresh the same environment.
The lock includes platform wheel hashes for macOS ARM64/x86_64 and Linux. If your Python
installer cannot find a compatible wheel, stop and diagnose rather than disabling TLS or
hash verification. Dependencies need Internet only during setup; demo/tests run offline.
Maintainers can regenerate the lock with
`uv pip compile pyproject.toml --python-version 3.12 --universal --generate-hashes --output-file requirements.lock`.
Changing the lock changes the release digest and requires fixture review.

`demo.sh` launches a real SDK stdio subprocess, sends `server/discover`, lists exactly one
tool, calls it, validates its structured output, prints the observed revision and response,
and shuts down the child. It explicitly sends discovery on the wire: a pinned SDK client
can synthesize capabilities, which by itself would not prove discovery occurred.
The server's stdout is reserved for MCP; audit JSON goes to stderr.

## Optional loopback Streamable HTTP

In terminal one, from `Part1C/`:

```bash
PYTHONPATH="$PWD/src" .venv/bin/python -m swda_part1c.server --transport streamable-http
```

In terminal two, from the same directory:

```bash
./demo.sh --url http://127.0.0.1:8765/mcp
```

Stop terminal one's server with Ctrl-C. Host is fixed to `127.0.0.1`; no public-bind
option is offered. The SDK's Host/Origin protections remain enabled. This endpoint has
no enterprise authentication: processes on the same host share a simulated local scope.
Never forward or expose it to other machines, use real citizen records, or treat a
client-supplied string/header as an authenticated identity.

## Contracts and deterministic rules

Only `recommend_service` is public. Its SDK-generated input schema wraps the business
request as `{"request":{"request_id":"example-001","request_text":"job search","channel":"web"}}`.
Request IDs are 1–64 ASCII letters/digits/underscores/hyphens; text is 1–2000 characters
and nonblank; channels are `web`, `phone`, `caseworker`. Unknown business/wrapper fields
are rejected. Do not put sensitive information in IDs. There is no caller identity field.

Rules **1.0.0** tokenize ASCII words case-insensitively and count **distinct** keyword
matches. Explicit evaluation priority is employment, skills, care. Employment keywords:
`job employment unemployed career`; skills: `training course skills reskill`; care:
`caregiver caregiving respite`. The unique highest count wins. Equal highest counts
abstain as `ambiguous`; zero matches return `unknown`. Repetition never increases a
category's score. These lexical rules cannot understand negation, multilingual intent,
context or adversarial semantics; they are not calibrated ML confidence scores.

Catalogue **synthetic-1.0.0** contains entirely invented names, examples and identifiers.
Internal `lookup` reads only the bundled, bounded JSON catalogue. It filters by active
status, exact category and supported channel, then sorts by ascending `(priority,
programme_id)` and returns at most three matches. This is programme routing, **not a
benefit eligibility assessment**. No age/income/citizenship assumptions are inferred.
Every response says `advisory: true` and supplies stable reason codes and versions.
Ambiguity returns `human_review`; unknown categories or no programme match return
`abstained`, with `requires_human_review: true`. The host/operator must arrange the human
review; this demo does not send referrals. Identical business inputs and artefact versions
produce identical business output, apart from trace IDs.

## Governance and failure handling

The execution order is SDK dispatch → strict input validation → fresh runtime policy →
agent → internal classify → internal lookup → validated structured output → metadata audit.
Discovery (`server/discover` and `tools/list`) also checks fresh policy; denied discovery
returns a sanitized MCP error rather than exposing the tool listing. Cache hints are
private with zero TTL. Call-time approval is mandatory even after prior discovery.

The version-controlled [approval fixture](policy/approved_agent.json) is conspicuously
synthetic: fictional signers and `PUBLISHED` state simulate A3, without signatures or
independent administration. It expires **6 November 2027 at 00:00 UTC**. Expiry, missing,
corrupt or unavailable policy, wrong scope, revoked/suspended state, wrong digest or tool
schema all deny. `APPROVED` alone does not permit execution. No runtime self-approval or
publication API exists. The offline state-machine module checks the ten A3 states,
permitted transitions, roles and developer separation; role strings there are test
inputs, not authentication credentials.

Release SHA-256 covers sorted POSIX relative paths for all `src/swda_part1c/*.py`,
`data/synthetic_programmes.json`, `pyproject.toml`, `requirements.lock`. Each file is hashed
as UTF-8 relative path + NUL + ASCII byte length + NUL + exact bytes. Symlink source
artefacts are rejected. Approval, docs, scripts, tests, caches and `.venv` are excluded to
avoid circular approval hashing. The fixture separately binds the exact SDK-generated
input/output schemas through sorted compact JSON SHA-256. The runtime recomputes these
bindings on every discovery/call; it never auto-approves changed code.

After an intentional source/lock change, a developer can **inspect**, not automatically
approve, the new digests:

```bash
PYTHONPATH="$PWD/src" .venv/bin/python -c 'import asyncio; from swda_part1c.artefacts import digest, schema_digest; from swda_part1c.server import build_server; print(digest()); print(schema_digest(asyncio.run(build_server().list_tools())))'
```

A human must review fixture changes and rerun all tests. Changing an existing synthetic
fixture is a demo maintenance operation, not evidence of a valid production approval.
Real deployments require a new immutable version, independent signoff and attestation.

Errors are sanitized MCP errors with `category` and `trace_id`: `validation`,
`policy_denial`, `dependency_failure`, `internal_failure`, `unsupported_protocol`.
Normal no-match is a business response, not an error. Request/result sizes, catalogue
size, file reads, worker concurrency (four) and caller execution deadline (three seconds)
are bounded. HTTP body limit is 16 KiB and tool result limit 16 KiB. A worker abandoned
at deadline may finish its already-running read-only work; Python threads cannot be
forcibly cancelled. The demo has no external side effects. See limitations below.

## Review and evidence

- [Architecture traceability](docs/architecture_alignment.md)
- [Security and platform limitations](docs/security_limitations.md)
- [Executed test evidence and five-perspective review](docs/test_evidence.md)
- [AI assistance disclosure](../README.md#ai-assistance)

`test.sh` runs Ruff formatting/lint, unit tests, contract/security negatives, actual SDK
stdio subprocess and loopback HTTP protocol tests. Native macOS results are not inferred
from Linux; the repository CI includes separate macOS Intel and ARM64 jobs.
