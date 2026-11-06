# SWDA Part 1A — Revised Architecture Notes

**Baseline:** 6 November 2026 (Asia/Singapore)  
**Status:** design-submission candidate; **not** production approval or proof of deployed controls  
**Originals:** revision of the existing four Mermaid sources and review package; no source reconstruction necessary  
**Scope:** Part 1A architecture only. Part 1C coding is deliberately excluded.  
**Target MCP protocol:** `2026-07-28`, conditional on interoperability through the actual Unity Gateway endpoint.

## 1. Architectural model

| Diagram | Question answered | Principal boundaries |
|---|---|---|
| **A1** Enterprise AI | How service requests reach validated data, models and recommendations, and how agents access catalogue data separately | Business / AWS / Databricks / SWDA governance / Unity Gateway / private MCP backend / future online |
| **A2** MLOps lifecycle | How code and models are tested, promoted, monitored and recovered | Development (CI), Staging (CT and evidence), Production (CD, scheduled inference and AIOps) |
| **A3** Agent registry and admission | Which immutable agent artefact can be published, by whom, and how it is suspended | SWDA human approval registry vs publication controller vs Unity Catalog MCP Service vs backend policy enforcement |
| **A4** MCP runtime | How authorised clients discover tools, invoke recommendations and encounter controlled errors | Business user / host / client / Databricks OAuth + UC gateway / SWDA policy authority / private server / internal tools |

**Visual key.** Solid arrows denote logical data paths, invocation or state transitions; dotted arrows denote controls, auditing or corrective proposals. Heavy A1 arrows are **future online** paths, not the initial batch deployment. Each diagram is a logical architecture and not a claim that SWDA already owns the depicted services. MCP enterprise access is a proposed subsequent capability, distinct from the release-one hourly batch.

### A1 — Enterprise AI architecture

Approved source connectors land service requests, catalogue changes and outcomes in **Amazon S3**. Data validation, duplicate suppression and quarantine precede Delta **Bronze → Silver → Gold**. Versioned features and programme catalogue snapshots feed two distinct consumers: (1) governed MLflow/Unity Catalog model development followed by a **pinned, hourly Lakeflow Jobs batch** producing versioned recommendations; and (2) a minimal read-only catalogue service exposed to the Service Recommendation Agent through **deterministic** internal tools. The MCP invocation does **not** initiate model retraining and has no raw S3 or enterprise-database credentials.

Each batch should carry input watermark, catalogue version, model version, rule/configuration digest, feature version, Git SHA, job ID and output run ID. Consumer feedback re-enters controlled ingestion and evaluation. Both private-network enforcement and catalog permissions are needed: a business-facing MCP host may never connect directly to the backend or raw data. A separate SWDA approval controller reconciles Gateway admission settings and independently attested backend versions. Proposed online serving is shown only as a future branch.

### A2 — MLOps lifecycle

**CI** covers code formatting, static/type checks, dependency and vulnerability scans, tests and security verification. Passing code enters **staging**; **CT** trains against versioned datasets, feature transformations, code, randomness controls and configurations. **MLflow** records evidence; the **Unity Catalog model registry** records candidate model versions. A release gate compares the candidate with an approved production baseline for task quality, reproducibility, security, data-governance, operational readiness and relevant responsible-AI evidence. Human promotion approval is required whenever release policy prescribes it; otherwise the preapproved gate policy must be recorded.

**CD** packages a compatible, approved *release manifest* (code, model, feature schema, catalogue/rules and configuration), rather than a floating model alias alone. **Lakeflow Jobs** schedules hourly work. Idempotent Delta upsert/MERGE, event-time watermarks, deduplication and delivery identifiers permit replay without duplicate business effects. Health and drift alarms trigger either incident containment, rollback to the last approved *compatible* manifest, or a **retraining proposal** that returns through CT and every approval gate. Scheduler retries are not a substitute for downstream delivery idempotency. The diagram intentionally avoids an automatic retrain-to-production shortcut.

### A3 — SWDA agent approval registry and publication

**SWDA owns the authoritative approval record**, not Unity Gateway. Its minimum record is: agent ID; semver; owner and business purpose; immutable source/container artefact digest; tool names and JSON Schemas; downstream tool allowlist; permissions and data classification; approved host service-principal IDs; evaluation/security evidence; independent human approval decisions, signers and timestamps; environment; expiry; revocation and suspension status; and linked deployment/configuration version.

States are **DRAFT → REGISTERED → VALIDATED → SECURITY_REVIEWED → APPROVED → PUBLISHED**, with explicit **REJECTED, SUSPENDED, REVOKED, REAPPROVAL_REQUIRED** outcomes. Developer and approver identities must differ; the agent cannot write its own approval or publication status. Unit, integration, contract/schema, dependency-vulnerability, tool-authorization, prompt-injection/malformed-input (as applicable), evaluation, telemetry, audit and operational tests precede approval. A security/data-governance reviewer clears risk, followed by an independent business owner. A new code digest, tool schema, permission, client scope, sensitive-data behaviour or material policy change requires a **new immutable version and renewed review**.

**Publication controller (SWDA-owned) — proposed implementation contract:**

1. Obtain authoritative approval for an **exact** `(agent_id, semver, artefact digest, environment, approved tools, client principals, policy revision, expiry)` tuple; perform a separation-of-duties check.
2. Verify the deployed backend image/artefact digest against the signed manifest; fail admission if unverifiable. No Mutable `latest` tag can substitute for digest attestation.
3. Create/update the **Unity Catalog MCP Service** only through the restricted administrative identity. Reconcile its HTTP connection, **explicit non-empty exact tool selectors**, `EXECUTE` grants and relevant `USE CATALOG` / `USE SCHEMA` grants; keep **automatic inclusion of newly added tools disabled**. End users must not receive `USE CONNECTION`.
4. Restrict the backend to authenticated gateway-managed traffic over a verified private route and allowlisted outbound destinations. Read back Gateway configuration and backend deployment identity before committing `PUBLISHED`.
5. Record the approval, attempted reconciliation, readback, publication and failure decisions in SWDA audit. Publication failure retains a nonpublished/reapproval-needed state. Drift between approved manifest and deployed configuration triggers suspension rather than silent repair that could widen access.
6. For **SUSPENDED, REVOKED, expired or changed** versions, the SWDA **backend runtime PEP** independently checks an authoritative, fresh decision for **every** `tools/call` (and for discovery), rejects on missing or stale policy and denies new invocations. The controller also removes Gateway exposure/grants as a second line of defence; do not assume this update is instantaneous.

**Revocation contract:** no positive authorisation cache is accepted for production until a bound and invalidation mechanism is proven; the preferred baseline is read-through to an authoritative strongly consistent policy endpoint with fail-closed errors. After an administrative revocation transaction commits, **every newly started** invocation must be denied at the private backend. Already executing calls require separate bounded execution, cancellation and timeout tests; no immediate termination guarantee is claimed. A discovered or cached tool may remain visible briefly, but cannot execute after revocation. Use private cache hints (prefer `ttlMs: 0` where the protocol supports them) and explicit client refresh on policy change.

**Trust split:** Unity Gateway enforces its documented UC identity/grant, tool-selection, credential proxy, audit and optional configured service-policy controls. SWDA's **own** controller and private runtime PEP enforce business approval, exact digest, expiry, approval revision, environment, service identity and deterministic tool allowlists. The gateway is not assumed to call an arbitrary SWDA approval API natively.

### A4 — MCP discovery and invocation

The business user authenticates to the enterprise **host**. The host checks business-user permissions, then its embedded **MCP client** uses a **dedicated host service-principal** Databricks OAuth M2M token. The initial design does **not** rely on unverified end-user identity propagation into the custom MCP server: Unity Gateway authorises the host principal using catalog and MCP-Service grants; the backend separately authenticates the gateway-to-backend service identity and checks the SWDA approval registry, including the actual deployed digest. A future delegated-user approach must demonstrate trusted identity propagation and correct authorization semantics before use; client-supplied user strings, metadata or headers are **not trustworthy proof**.

The `2026-07-28` sequence allows optional `server/discover`, followed by permitted `tools/list` and per-invocation `tools/call` of `recommend_service`. Modern Streamable HTTP requests must carry appropriate protocol-version/method headers and self-describing client metadata; mandatory legacy `initialize` / `initialized` is **not** shown. Gateway UC grants and configured selectors are checked independently of the SWDA backend PEP. Approval status is rechecked for tool calls regardless of prior discovery or cache. The private server validates request and result JSON Schemas and constraints; the agent uses only the deterministic classifier and curated catalogue lookup. Responses carry structured provenance and safe errors. Both Gateway and SWDA record trace IDs, decisions and status, not raw secrets.

**Audit privacy caution:** Databricks unified traces can contain request and response payloads, including sensitive values; default trace capture is **not** evidence of redaction. Review trace-table configuration, access permissions, capture mode, retention and redaction before production; limit SWDA application logs to metadata. Policy-denial responses may be JSON-RPC errors or Databricks policy result envelopes, not necessarily HTTP 403; clients must inspect the real protocol-level result.

## 2. Vendor capability vs SWDA responsibility

| Control | Documented Databricks capability | Additional SWDA-specific enforcement / validation |
|---|---|---|
| External server registration | Unity Catalog **MCP Service** references HTTP connection; **Streamable HTTP** required | Publication controller verifies exact approved artefact and prevents self-service bypass |
| Gateway authorisation | Caller Databricks token (user or service principal); `EXECUTE` MCP Service plus parent `USE` grants | Dedicated approved host principals; host checks business-user access; no arbitrary end-user propagation claim |
| Tool exposure | Explicit tool selection; unselected tools hidden from `tools/list` and refused on `tools/call` | No wildcard/empty selectors; compare runtime tool schema and exact manifest at backend |
| Tool policies | **Beta** Gateway service policies: ON CALL/ON RESULT; custom function/external vendor endpoint possible, subject to preview | Optional defence-in-depth; **not** required for baseline. Do not assume arbitrary SWDA approval API callback or instant propagation |
| External policy API | Beta vendor-style `ALLOW`/`DENY`/`ASK` contract, OAuth M2M connection; external policy attachment documented as UI-only | Only enable after workspace verification; treat any latency / attachment change as operational change; backend PEP remains mandatory |
| Credentials | Gateway manages outbound connection credentials; per-user or shared provider identity depending on connection mode | Choose dedicated backend service principal for initial release; authenticate private backend ingress; verify tenant/user semantics separately |
| Logs and observability | `system.ai_gateway.usage`, `system.access.audit`, optional unified traces | SWDA approval decisions, controlled trace schemas, data minimisation and sensitive-log safeguards |
| Suspension/revocation | Admin update/delete, grant changes and tool-selection updates are supported; propagation timing not guaranteed | Immediate-after-commit **new-call** denial at SWDA backend via fresh authoritative policy; Gateway reconciliation secondary |
| MCP protocol 2026-07-28 | Databricks docs establish Streamable HTTP, not verified end-to-end **modern** lifecycle support in this workspace | Compatibility gate with pinned SDK, proxy, error mapping, discovery/header and legacy downgrade tests |

**Important limitation.** Vendor documentation reports an external service-policy propagation window (typically **60–90 seconds**) and Beta/UI-only attachment constraints. Those hooks **cannot serve as SWDA's sole revocation authority**. The backend runtime PEP is an explicitly proposed SWDA component. The SWDA release controller must not promise automated attachment/update of external policies if the selected vendor surface cannot automate it.

## 3. Architecture decisions and trade-offs

| Decision | Rationale | Trade-off / guardrail |
|---|---|---|
| Hourly Lakeflow batch first | Matches assessment, auditable jobs and lower initial operational surface | Not interactive scoring. Watermarks and lateness handling required |
| S3 + Delta Bronze/Silver/Gold | Separation of raw, validated and curated data with versioned lineage | Storage/compute costs, retention, vacuum and access governance need policy |
| MLflow + UC model registry | Reproducible candidate evaluation and governed model versions | A registered model is not automatically a human-approved production release |
| Pinned release manifest | Prevents rollback to mismatched code/features/rules/model | More release metadata and coordinated rollback |
| Deterministic catalogue tools | Testable business rules, minimal read permissions | Limited flexibility; future generative tools need fresh validation/approval |
| SWDA approval registry + admission controller | Separates business approval from vendor technical publication | Additional small control-plane component and operational responsibility |
| Backend PEP even behind Gateway | Fail-closed business policy when Gateway external policy integration is absent/unproven | Per-call policy latency and dependency; fail-closed impact requires availability design |
| Host service principal baseline | Gateway can grant a defined client identity without assuming user delegation | Individual end-user authorisation remains a host obligation; stronger per-user audit/delegation is later integration work |
| Gateway-managed credentials and private backend | Reduces client credential exposure and bypass paths | Private route/network and identity must be verified for actual workspace |
| Future online serving held separately | Avoids treating roadmap features as release-one prerequisites | Require new latency, capacity and operational acceptance criteria |

## 4. Non-negotiable security and reliability properties

- No raw S3, Delta, DB or arbitrary enterprise tools accessible to the MCP client or agent. The only catalogue interface is a restricted **read-only curated view/service** with dedicated least-privilege credentials.
- Separate the ML model registry, SWDA agent approval registry and Unity Catalog MCP Service registration. None implies approval in another system.
- No developer self-approval, no agent write access to its own registry status, no broad `USE CONNECTION` privileges for consumers, and no direct public backend ingress.
- Reject unknown registered versions, incorrect digest/attestation, unlisted tools, unauthorised host service principals, stale/expired policy, unreachable policy service, invalid schemas and unexpected protocol revisions.
- Record immutable business approval evidence and operational status with trace correlation, but not credentials/raw sensitive payloads in routine logs.
- Idempotent batch processing, watermarks, durable run manifests, dead-letter/quarantine routes, pinned compatible rollback and controlled re-delivery are required; specific RPO/RTO/SLO values are **not assumed**.
- Responsible AI evidence should include error/coverage by appropriate reviewed groups, abstention/escalation policy, human appeal and outcome reviews when relevant and legally approved, without inventing observed fairness metrics.
- For synthetic local Part 1C, retain the same deterministic tool schemas and deny-by-default contracts, but do not require AWS/Databricks deployment.

## 5. Deployment acceptance decisions still required

1. **Gateway interoperability:** demonstrate `2026-07-28` through the actual registered Unity Gateway service, not only direct to the SDK server. If incompatible, document a controlled **legacy-era** gateway boundary and keep `2026-07-28` as a roadmap target; a gateway that silently downgrades is not accepted.
2. **Network ingress:** validate that the workspace can reach the private backend under approved routing while direct Internet access, unauthorized UC connections and unapproved clients cannot.
3. **Identity:** verify exact issuer/audience and M2M token constraints, service principal mapping, whether OAuth client IDs are available to policies, and user-to-host authorization assurance.
4. **Revocation:** load-test fresh backend policy calls; verify deny-after-commit for new calls, stale cache behaviour, gateway control propagation, in-flight deadlines and fail-closed outage handling.
5. **Observability/privacy:** approve access, retention and redaction for Gateway usage/audit/traces and SWDA-controlled logs.
6. **Data/operations:** confirm source contracts, classifications, programme ownership, schedule cutoffs, acceptance metrics, alert thresholds, backup/restore targets, on-call roles and cost limits.

## 6. Part 1 requirement coverage

| Assignment item | Diagram coverage | Interpretation |
|---|---|---|
| 1. Data/feature pipelines | **A1**, A2 | Landing, validation, Bronze/Silver/Gold, features |
| 2. Experiments/evaluation/models | A1, **A2** | Reproducible MLflow, baseline comparison |
| 3. Model/prompt/artefact management | A1, **A2**, A3 | Registry, compatible manifests; prompts where applicable |
| 4. CI/CD/CT + release gates | **A2**, A3 | Separate gates and explicit rejections |
| 5. Batch and future online serving | **A1**, A2 | Hourly now; future online clearly isolated |
| 6. Monitoring/alerting/incidents | A1, **A2**, A4 | Runs, drift, audit and safe failure |
| 7. Drift/feedback/retraining | **A1**, **A2** | Proposal loops into evaluation/approval |
| 8. Security, audit, responsible AI | A1, A2, **A3**, **A4** | UC, approval, revocation, private tool/data access, evaluation |
| 9. Reliability/recovery/cost | A1, **A2**, A4 | Idempotent replay, rollback, cost telemetry, fail-closed |
| 10. Agent registration/approval/MCP | A1, **A3**, **A4** | Human approvals, controller, gateway, backend enforcement |
| 11. Hands-on coding | A1/A3/A4 **interfaces only** | Deliberately **not implemented** in Part 1A |

**Part 1A deliverable:** principal flows A1/A2; registry and approvals A3; MCP host/client/server/agent/tools and secured discovery/invocation A4. Part 1B must elaborate design justifications; Part 1C must provide its own runnable thin-slice evidence.

## 7. Authoritative references (retrieved 2026-11-06)

1. [SWDA assessment](https://drive.google.com/file/d/1lkvguwI3463kXyKKl-BLXR5WAhbeSIHI/view) — source of Part 1 scope and original release assumptions.
2. [Databricks — External MCP servers](https://docs.databricks.com/aws/en/ai-gateway/register-mcp-service) — Streamable HTTP, UC MCP registration, endpoint/connection requirements, grant and selector API.
3. [Databricks — Govern an MCP](https://docs.databricks.com/aws/en/ai-gateway/govern-mcp-service) — UC grants, tool selection, policy Beta, rate limits and system-table audit.
4. [Databricks — MCP authentication](https://docs.databricks.com/aws/en/agents/mcp-tools/authentication-networking) — inbound Databricks OAuth and outbound connection identities.
5. [Databricks — Service policies](https://docs.databricks.com/aws/en/data-governance/unity-catalog/service-policies) — phases, `ALLOW`/`DENY`/`ASK` behaviour and limitations.
6. [Databricks — External service policy](https://docs.databricks.com/aws/en/data-governance/unity-catalog/service-policies/external-policies) — external vendor interface, OAuth M2M, UI-only attachment and propagation caveat.
7. [Databricks — External policy API](https://docs.databricks.com/aws/en/data-governance/unity-catalog/service-policies/external-policy-api) — Beta endpoint contract.
8. [MCP — 2026-07-28 official release](https://blog.modelcontextprotocol.io/posts/2026-07-28/) — modern stateless lifecycle, discovery, headers and OAuth changes.
9. [MCP Python SDK — protocol versions](https://py.sdk.modelcontextprotocol.io/protocol-versions/) and [MCP TypeScript SDK v2](https://ts.sdk.modelcontextprotocol.io/v2/) — modern SDK support; **not** evidence of Unity Gateway interoperability.
10. [MCP TypeScript SDK — support for 2026-07-28](https://ts.sdk.modelcontextprotocol.io/v2/migration/support-2026-07-28) — header validation and modern/legacy distinctions.

