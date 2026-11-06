# Execution evidence and engineering review

Validation date: 6 November 2026 (Asia/Singapore). Execution host: Linux x86_64,
Python 3.12.14. Official MCP SDK 2.3.0; Pydantic 2.14.3; pytest 9.2.0; Ruff 0.17.4.

## Executed verification

From `Part1C/`: `./setup.sh`, `./demo.sh`,
`./test.sh --junitxml=test-results.xml`. Setup was repeated with the final lock;
`pip check` reported no broken requirements. All dependencies were installed with
exact pins and SHA-256 verification. The final setup also requires binary wheels.

| Check | Result |
|---|---|
| Ruff format | 15 Python files conform |
| Ruff lint | Passed |
| Functional/business contract tests (`test_engine.py`) | 28 passed |
| Registry, policy and release integrity (`test_governance.py`) | 55 passed |
| SDK, transports, robustness and security (`test_protocol.py`) | 31 passed |
| Total | **114 passed, 0 failed, 0 errors, 0 skipped** |
| Shell syntax (`bash -n setup.sh demo.sh test.sh`) | Passed on available Bash; not native Mac Bash |
| Git whitespace checks | Passed |
| Part1A/B comparison against base | No changes |

The stdio demo's actual SDK client printed `observed_protocol: 2026-07-28` after a wire
`server/discover`, `tools/list` and `tools/call`. The HTTP integration performed the same
operations through a real loopback server process and asserted the connected client's
revision and structured recommendation. Auto-discovery is also tested, while legacy
initialize is explicitly rejected. Version pins alone are not the evidence: tests send
the protocol requests, assert returned discovery revisions, and require a successful
call through a middleware that rejects every other revision. Normal operations use the
official SDK, not handcrafted JSON-RPC. Only malformed/header security tests use raw HTTP.

The demo recommends `SYN-E01` then `SYN-E02` for the synthetic job enquiry; outputs are
validated as `RecommendationResponse`. Other tests cover care, skills, unique-token
scores, ties, unsupported categories, inactive programmes, channel conditions, stable
ranking, repeatability, missing/malformed/extra/oversized inputs and bounded outputs.

Security tests deny every non-PUBLISHED state, changed version/digest/schema/internal
allowlist/service/client/environment scope, expired policy and missing/corrupt/oversized
or unreadable policy. They exercise denied discovery and calls **after earlier successful
discovery**, including a real stdio child whose temporary policy is revoked while it
remains running. Repeated subsequent calls fail. Actual deployed source mutations change
the digest; policy changes do not create a circular digest. Unknown/internal/admin tools
are denied; accidental public-tool registration causes discovery to fail closed.

Other checks inject catalogue and internal failures; assert sanitized errors and metadata
logs exclude secret sentinel strings, paths and request contents; verify response/audit
trace correlation; enforce worker capacity and a real execution deadline; reject hostile
Host/Origin and mismatched protocol/method headers; reject HTTP bodies above 16 KiB;
and run an actual Bash demo launcher in a repository path containing spaces. Header
negative tests first prove their otherwise identical baseline request succeeds.

## macOS evidence and limits

Cross-platform wheel resolution/download **passed** for both
`macosx_15_0_arm64` and `macosx_15_0_x86_64`, using Python 3.12/CPython tags,
`--require-hashes --only-binary=:all:` and the final lock. Wheels were downloaded and
verified, not executed. A first attempt exposed that cryptography 50.0.2 lacks compatible
Intel wheels; the final explicit pin is **48.0.1**, which supplies a universal2 wheel.
The final set resolves without requiring a compiler for either supported Mac target.

GitHub Actions has Ubuntu, macOS 15 ARM64 (`macos-15`) and macOS 15 Intel
(`macos-15-intel`) jobs. Runner labels were checked against the official runner-images
inventory; retired macOS 14 was removed during review. Native Mac execution and CI
outcomes remain **unverified** until those jobs or an actual Mac run complete. No Mac
test passes are claimed from Linux or from wheel availability.

The cloud command sandbox prohibited AF_INET sockets and interfered with async I/O,
causing early transport failures. The full passing suite ran in the actual cloud machine
with permitted local sockets/subprocess I/O. No tests were skipped or assertions weakened
to accommodate those restrictions. Initial application/test defects were repaired, then
the complete suite rerun. Current-run JUnit XML is generated locally (ignored in Git) and
uploaded by CI when a job runs.

## Five-perspective review

These are explicit review passes by the implementing AI acting in different roles,
not separate independent humans or third-party certification.

| Perspective | Finding and correction | Residual limit |
|---|---|---|
| Principal engineer | Small SDK adapter/internal engine split; strict contracts and explicit priorities. Corrected dictionary-vs-model assumption in SDK middleware results. | Keyword coverage/negation limited; routing is advisory only. |
| MCP architect | Real v2 Client tests on both transports; pinned modern mode plus forced wire discovery. Synthetic pinned-client discovery alone was rejected as evidence. | Unity Gateway interoperability remains untested. |
| Security engineer | Fresh exact fixture checks before discovery/calls, source/schema binding, denied widening and failure sanitization. Validate engine output before SDK conversion to avoid SDK exception payload logging. | Local mutable fixture is not independent approval, attestation or authentication. |
| AIOps/SRE engineer | Repeatable hash-lock setup, JSON audit correlation and bounded responses/workers. Added operation labels so later discovery cannot be confused with a call audit event. Abandoned threads retain physical work slots. | No distributed quotas, durable audit store or hard thread kill; availability fails closed. |
| Independent examiner | A1/B scope retained; traceability records implemented/simulated/designed/unverified separately; AI use disclosed. Caught Intel wheel incompatibility and obsolete CI label before delivery. | Native Mac and all enterprise go-live gates remain open. |

No known failing local application tests remain. Production security, compliance,
classification quality and independent approval are not established by this demonstration.
