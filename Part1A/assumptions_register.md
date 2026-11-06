# SWDA Part 1A — Facts, Proposals and Unverified Dependencies

**Reviewed 6 November 2026.** An assessment fact is not a claim of deployed infrastructure; a vendor product capability is not proof it is enabled in SWDA's tenant.

## A. Explicit assignment facts

| ID | Assessment fact | Implication |
|---|---|---|
| F01 | AWS and Databricks are the intended data-platform context | All designs use these platform boundaries |
| F02 | Existing prototype classifies service requests and recommends programmes/services | Deterministic/recommendation flow is the business capability |
| F03 | First release uses hourly batch inference | A1/A2 treat the hourly schedule as release-one production |
| F04 | Near-real-time API and approved MCP agents may follow later | A1 marks future online; MCP is proposed, not current deployment |
| F05 | Data may be sensitive; reliability, audit, security, observability and costs matter | Default-deny, telemetry, data minimisation and recovery are mandatory design goals |
| F06 | Part 1A diagrams must show principal flows, agents, registry, clients, approval and MCP | A1–A4 jointly cover these concerns |
| F07 | Part 1C asks for a small synthetic, locally runnable MCP agent | This package is architecture-only; no coding claimed |

## B. Proposed architectural decisions

| ID | Proposed assumption/decision | Rationale | Depends on | Production verification |
|---|---|---|---|---|
| D01 | S3 landing, Delta Bronze/Silver/Gold | Versioned, auditable data refinement | F01, F05 | Source contracts, retention, connectivity, UC permissions |
| D02 | Databricks Lakeflow Jobs for hourly batch | Managed scheduled orchestration | F03 | Tenant SKU, job permission, lateness/replay tests |
| D03 | MLflow plus UC governed model registry | Tracks evidence and versioned candidates | F01 | Catalog privileges, lifecycle and environment isolation |
| D04 | Pinned release manifest for model/code/features/catalogue | Rollback compatibility and reproducibility | D03 | Artefact signing, immutable tags, reconciliation tests |
| D05 | SWDA registry separate from model registry and MCP Service | Human business approval independent of vendor publication | F06 | Registry persistence, authorization, role separation |
| D06 | SWDA admission/publication controller | Restricts service creation and selector/grant changes to approved manifest | D05 | Admin API, readback, unauthorized publication denial |
| D07 | Private MCP server with SWDA runtime PEP | Fresh digest/status/expiry/allowlist enforcement independent of preview hooks | D05, D06 | Authenticated backend identity, private routing, revoke/fail-closed tests |
| D08 | Approved host OAuth M2M principal baseline | Avoids relying on unverified delegated-user propagation | D07 | Principal-specific UC grants, service token scope, host user auth |
| D09 | Restricted read-only programme catalogue interface | Keeps MCP tools deterministic and least privileged | D01 | Data classification, query role, negative tests |
| D10 | Gateway MCP service with exact tool selectors, auto-include disabled | Known vendor control, prevents surprise new tools | D06 | Workspace API, tool selector `tools/list`/`tools/call` tests |
| D11 | No positive runtime policy decision cache until verified | Avoids stale approval after revocation | D07 | Strong-consistency, outage, latency and load tests |
| D12 | SDK/server target MCP `2026-07-28` | Modern protocol revision specified by task | D07 | End-to-end proxy and client compatibility tests |
| D13 | Online API/serving is a future, separately approved release | No invented latency requirement | F04 | Capacity, authorization, SLO and data freshness design |

## C. Unverified dependencies and go-live blockers

| ID | Missing confirmation | Risk if false | Safe mitigation | Verification owner/test |
|---|---|---|---|---|
| U01 | Unity Gateway tenant/region and MCP registration available | Cannot expose registered custom server | Do not publish; run local MCP proof of concept | Databricks platform admin: create/read/delete sandbox MCP Service |
| U02 | Unity Gateway `2026-07-28` modern wire handling | Discovery, headers or stateless requests rejected | Gate release; explicit documented legacy-only compatibility branch | MCP lead: actual gateway end-to-end protocol matrix |
| U03 | Private Databricks-to-MCP backend route and authenticated ingress | Direct backend bypass or unavailable service | Deny public ingress, private networking, backend identity check | Security/platform: route and unauthorized access tests |
| U04 | Gateway propagation/revocation semantics | Stale discovery/permissions | Backend read-through authoritative policy each call; fail closed | SRE/security: revoke during active traffic, check new-call denial |
| U05 | Availability and permissions for Beta external policies | Cannot rely on Gateway callback to SWDA | **Do not require** Beta hook for core approval; optional later defence | Workspace admin: check preview/config, policy test |
| U06 | Trusted end-user identity propagation to backend | Per-user backend checks may be spoofed or impossible | Baseline host/service-principal boundary; no user delegation claim | Security: signed-claim provenance and impersonation tests |
| U07 | Source schemas, data class, programme authority, output SLA | Inaccurate lineage or over-broad access | Least privilege, agreed contracts, quarantines | Data owner: contract, retention, quality tests |
| U08 | Model/recommendation acceptance and fairness thresholds | Unbounded quality/ethical risk | Explicit human-approved thresholds before promotion | Business/model-risk owner: evaluation protocol |
| U09 | Recovery targets, on-call and spend constraints | Insufficient incident response | Pinned rollback, idempotent replay, alerts, planned limits | Operations: game day and finance sign-off |
| U10 | Databricks trace payload privacy configuration | Sensitive content persists in monitoring stores | Disable/unredact only under approved purpose, access and retention | Security: inspect actual trace rows and controls |

**Approval principle:** all unverified dependencies must be either demonstrated or addressed by a tested fall-back before production. In particular, U02–U04 block a claim of complete operational MCP interoperability and revocation assurance.
