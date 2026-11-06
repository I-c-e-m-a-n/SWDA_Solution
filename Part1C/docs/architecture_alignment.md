# Architecture-to-implementation traceability

Sources inspected before implementation: root README; all four Part1A Mermaid sources;
architecture notes and assumptions; entire extractable text of the 28-page Part1B PDF,
particularly §§3, 5, 6, 8, 9, 10. Existing sources remain authoritative and unchanged.
Part1C supplies the local coding evidence that Part1B deliberately left pending.

| Authority / obligation | Actual implementation | Evidence / status |
|---|---|---|
| A1 MCP path; Part1B §3.3, D09 | `server.py` → `agent.py` → internal `classifier.py` / `catalogue.py` | Implemented locally; functional + protocol tests |
| A1 restricted curated service; §3.4 | Fixed bundled `data/synthetic_programmes.json`, validated catalogue and bounded advisory response | Synthetic stand-in, not an official catalogue or binding eligibility |
| A1 hourly batch / A2; §§3.2,4 | No AWS, Delta, training, Lakeflow, MLflow or production model imports | Designed only; deliberately outside Part1C |
| A2 CI gate; §§4.1,9 | `test.sh`, hash-pinned lock, GitHub Actions | Local checks executed; native macOS CI results separately pending |
| A3 ten-state registry; §5.1 | `registry.py` state/role/independence transition validation | Tested simulation, not administrative authentication |
| A3 exact immutable manifest; §5.2 | `artefacts.py`, exact code + dependency + catalogue and schema digests | Tested local disk-integrity binding; not signed workload attestation |
| A3 publisher/readback | `policy/approved_agent.json` explicitly fictional PUBLISHED record | Simulated; no Gateway publisher, UC selectors/grants or readback deployed |
| A3/A4 fresh policy; §5.3, D07/D11 | `policy.py` bounded per-request reads; `Governance` SDK middleware | Tested states, expiry, scopes, outages, drift and discovery-then-revocation |
| A4 discovery + calls; §6.2, D12 | Official v2 `MCPServer` + `Client`, real `server/discover`, `tools/list`, `tools/call`; modern-only service | Actual subprocess stdio + loopback Streamable HTTP; no required initialize |
| A4 host/backend identities; §6.1, D08/U06 | Server-owned `trusted-local-host` process scope; request has no identity field | Local trust simulation only; no OAuth M2M or asserted end-user delegation |
| A4 safe error and audit; §§6.3,8 | Sanitized MCP errors, strict contracts, metadata JSON stderr audit, deadlines and sizes | Tested invalid inputs, failure leakage and execution deadline |
| §8.3 responsible AI | Explicit advisory, ambiguity/no-match escalation; deterministic reason codes | No fairness, accuracy, eligibility or calibrated confidence claims |
| §10 MCP-02/06/09 enterprise gates | No Unity Gateway, enterprise network or identity integration | Unverified; all U01–U10 enterprise dependencies remain open |

Part1B's proposed runtime tuple is represented by agent ID/version/digest, environment,
fixed service scope, trusted local host scope, tool/schema scope, expiry and policy
revision. It is not described as cryptographically verified inbound Gateway identity.
The SDK middleware intercepts **before** params validation/handler execution, using its
documented `(ServerRequestContext, CallNext)` extension. It validates business inputs,
checks policy for both discovery operations and every call, then lets the SDK handle
protocol schemas/dispatch and transport framing. SDK-serialized results are revalidated
before release. Internal functions never appear in `tools/list`.

Local analogues cover aspects of MCP-01/03/04/05/07/08/10/11/12, with tests named in
`tests/test_protocol.py` and `tests/test_governance.py`. They do not close enterprise
tests bearing the same labels. In particular real Gateway modern-version/header/error
interoperability, linearizable revocation commits, propagation, private ingress, workload
attestation, token/grant semantics and trace privacy remain unverified. A local policy
file reread is not a strongly consistent replicated policy authority.

Official interface references checked 6 November 2026: [SDK repository/readme](https://github.com/modelcontextprotocol/python-sdk),
[PyPI stable release](https://pypi.org/project/mcp/2.3.0/),
[server guide](https://py.sdk.modelcontextprotocol.io/server/),
[client guide](https://py.sdk.modelcontextprotocol.io/client/),
[middleware guide](https://py.sdk.modelcontextprotocol.io/server/middleware/).
Released SDK 2.3.0 source was inspected for the exact middleware, modern client pin/probe,
result serialization, cache hints and transport security behavior and exercised in tests.
