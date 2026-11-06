# Evidence scope

This is historical architecture-only evidence. References to v2 inputs and offline verifier scripts describe source provenance; those inputs/scripts were not included in the source repository. Runtime verification is reported separately in [release verification](../docs/release-verification.md). Native Mermaid rendering remains unverified.

# SWDA Part 2A — Independent Architecture Verification and Targeted Patch Register (v3)

**Review date:** 6 November 2026, Asia/Singapore.  
**Classification:** **CONDITIONAL ARCHITECTURE PASS**, subject to native Mermaid rendering and implementation-level verification.  
**Assessment source:** *SWDA ML/AI Engineer Take-Home Assessment*, Part 2, including its illustrative Annex A MO-01–MO-08 and exercise-written, unverified Annex B S1–S5, accessed from the assessment's Drive PDF.  
**Revision scope:** The supplied `P2_A1_Simulation_Architecture_v2(2).mmd` and `P2_A2_Simulation_Sequence_v2(2).mmd`, their corresponding notes and SVG/PNG exports. Earlier similarly titled v2 `(1)` files were **not separately supplied as mounted files**; the attached `(2)` Mermaid sources were therefore used as the authoritative local v2 baseline. Part 1A artefacts were read only and **not edited**.

## 1. Summary of technical disposition

The v3 patch preserves the existing SWDA Part 2A actor categories, deterministic orchestrator, gateway-mediated messages, annex-only trust model, tagged hypothetical pattern cards, actor-removal experiments, non-authoritative reviewer, deterministic safety and evaluation gates, explicit human decision service, SQLite persistence design and six sequence phases. It does not introduce an enterprise platform, MCP dependency, extra autonomous agent, unapproved tool, production identity mechanism or real-model inference.

**All ten Part 2 assessment requirements remain architecturally represented.** Static Mermaid-source structure and source-derived SVG/PNG rendering checks pass. In particular, the corrected A1 reviewer route and A2 reviewer sequence now describe the same narrow read-only contract through the policy gateway. The detailed A1 remains extremely wide due to necessary cross-boundary and audit edges; a separate, compact-in-content executive overview is provided for presentation, while the detailed editable architecture and SVG remain authoritative.

**Material limitation:** Native Mermaid parsing and native Mermaid browser export were **NOT VERIFIED**. Chromium navigation to local and file URLs returned `ERR_BLOCKED_BY_ADMINISTRATOR`; no working Mermaid CLI could be used. The v3 A1 SVG/PNG were rendered with an **offline Graphviz source converter**; A2 was rendered with a **deterministic custom SVG sequence reconstruction** from the patched `.mmd`. These tools were independently checked for source node/edge or message/frame fidelity, but visual/layout fidelity to native Mermaid is not established. **None of the static checks proves actual runtime control enforcement, SQLite atomicity, fraud-detection quality or production suitability.**

## 2. Before → after correction register

| Required technical correction | v2 observed issue or limitation | v3 targeted modification | Evidence / disposition |
|---|---|---|---|
| A1 visual hierarchy and edge density | 35 nodes / 62 links with many long control/audit crossings; exports downscaled | Flowchart layout hints use left-to-right, straighter connectors and increased spacing; no semantic edge removed; new executive overview aggregates the **same** components | 35-node detailed technical view retained; 13-node conceptual executive view; SVG/PNG supplied. **PASS for availability; detailed readability remains qualified** |
| Trust-boundary clarity | A1 `REV` located with trusted `ANAL`; A2 `REV`, `SAFE`, `EVAL`, `APPR` in one labelled box | A1 adds `REVIEW` subgraph around existing `REV`; A2 separates deterministic analysis, isolated reviewer, assurance, and trusted human approval/persistence boxes | A1 11→12 trust subgraphs; A2 still 14 participants. **PASS (source and render)** |
| Narrow, consistent reviewer source lookups | A1 helpers reported directly to `REV` while A2 used `REV→POL→CAT→POL→REV` | A1 `REV→OUT→(MO/REF)→IN→REV`, with `CAT` accessed only by trusted helper; A2 `CAT` documented as including helpers, and `POL` validates reviewer identity/purpose/source IDs and filters returns | Exact A1/A2 arrow paths checked; no `REV↔CAT` direct edge. **PASS (source)** |
| Profile and ACL precision | Role labels did not fully specify incentive, capabilities, information, recipients, tools or prohibitions | Role-by-role table in A1 notes, clearly marked *simulation assumptions*, including reviewer; explicit gateway checks, source scope and optional 1/2/3 role participation | A1 notes, Section 3. **PASS (documentation)** |
| Recursive derived-run boundaries | CF and TEST execution described, but mode/origin/lineage restrictions and aggregate caps were insufficiently explicit | `CANDIDATE`, `CF`, `TEST`; parent ID + removed actor; depth-one CF; no recursive CF/TEST; no TEST review; taint-purged fresh context; hard individual and aggregate mock limits | A1 labels/notes Sections 5–6, A2 Phase 3 and 6 labels. **PASS (design), runtime NOT VERIFIED** |
| Trusted input digest | File hash alone did not prove correspondence to trusted expected version | Compare file digest to separately trusted, review-controlled, versioned expected manifest; missing/mismatched values deny | A1 loader label and Section 2; A2 CAT check. **PASS (design), actual digest validation NOT VERIFIED** |
| Local reviewer and atomic decision semantics | Potentially overbroad implication of enterprise authentication and runtime atomicity | Clarified *configured/locally verified PoC* role; explicit human action+rationale; persisted `REVIEW_PENDING`/passing gates; proposed SQLite CAS and committed receipt | A1 approval label/Section 6; A2 Phase 5. **PASS (design), SQLite tests NOT VERIFIED** |
| Image dimensions and rendering provenance | v2 notes called both full sequence SVG and PNG 3569×7933 | Corrected v2 SVG dimensions **3569×7933** and full PNG **921×2047**; source-to-render manifest records all v2/v3 files and SHA-256s; renderer described accurately | PIL/XML metadata, attached JSON manifest. **PASS** |
| Cross-diagram mapping | Some helper/gateway/persistence aliases were implicit | Explicit A1→A2 mapping below; no parallel ungoverned source or decision service introduced | Source adjacency checks and notes. **PASS** |
| Validation confidence | Diagram syntax/rendering could be mistaken for runnable policy/security tests | 10 requested gates classified below as PASS / FAIL / NOT VERIFIED, with separate runtime limitations | `verify_v3.py`, manifest JSON, current report. **PASS for honest verification scope** |

**No required functionality removed.** Two original helper→reviewer data arrows were **replaced**, not deleted without compensation: `MO` and `REF` outputs are now passed through `IN` after authorised `OUT` checks; four net operational connections were added. All other core run/evaluation/approval dependencies remain. A1 gains one trust subgraph but **no additional autonomous agent or mandatory deployment component**. There is no change to the separate Part 1A governed MCP source or exports.

## 3. Source counts and before/after inventory

| Quantity | Supplied v2 | v3 | Evidence |
|---|---:|---:|---|
| P2-A1 Mermaid logical nodes | 35 | **35** | Declaration parser; SVG `<g class="node">` groups |
| P2-A1 subgraphs | 11 | **12** | Separate `REVIEW` box; SVG cluster count |
| P2-A1 Mermaid links (all) | 62 | **66** | Endpoint-parser count; SVG edge group count |
| Operational links | 59 | **63** | Excludes 3 decorative legend links |
| v3 operational data / control / audit edges | — | **42 / 11 / 10** | Classified source arrow list; rendering style distinction |
| Optional executive overview | n/a | **13 nodes, 9 subgraphs, 23 links** | Same principal components aggregated; not an additional implementation |
| P2-A2 participants | 14 | **14** | Source participant/actor declarations |
| P2-A2 directional interactions | 100 | **100** | Source messages and 100 SVG `data-seq` groups |
| P2-A2 control frames | 14 | **14** | 9 `alt`, 2 `loop`, 2 `opt`, 1 `break` |
| Sequence phases | 6 | **6** | Explicit Phase 1–6 headings and exported phase PNGs |

The parser counted scripted actor self-invocations `TA→TA`, `PA→PA`, `EA→EA` as **local mock execution**, not actor-to-actor channels. There are no direct messages **between distinct simulated actors**.

## 4. Required ten-item assessment coverage

| Part 2 assessment requirement | v3 representation and proof boundary | Status |
|---|---|---|
| 1. Role-distinct actor profiles, information and capabilities | `TP/PP/EP` and `TA/PA/EA`; explicit A1 notes table plus `CTX` | **PASS — design coverage** |
| 2. Controlled actor-to-actor communication | `ORCH→OUT/IN` in A1, `ORCH↔POL↔TA/PA/EA` in A2; no direct peer channel | **PASS — source coverage** |
| 3. Actor boundaries / code-enforced least privilege | Isolated trust boxes, per-role ACL/schema/source restrictions and denial controls; **code enforcement not built** | **PASS — architectural design; NOT VERIFIED runtime** |
| 4. Pattern cards: actors, contributions, benefits and flows | `CARD`/`ANA`, typed card + provenance and missing test data | **PASS — design coverage** |
| 5. Actor removal / collusion versus single-actor misconduct | `DEP↔ORCH`, linked CF, fresh isolated context, descendant taint pruning, independent outcome | **PASS — source coverage; runtime NOT VERIFIED** |
| 6. Source / simulation / assumptions distinction | `LOAD/CAT` and `CARD` typed `SOURCE/SIMULATION/ASSUMPTION`; no fraud-as-fact output | **PASS — design coverage** |
| 7. Known / variation / new and test data needed | `MO/REF` trusted helper comparison + non-authoritative `REV`; sample-relative MO-01..08 only | **PASS — design coverage** |
| 8. Validated handoffs, retries, round/cost limits | `OUT/IN`, `ORCH`, `STATE`, bounded loop, retry branch, proposed lineage+TEST caps | **PASS — design coverage; runtime NOT VERIFIED** |
| 9. Hidden-instruction/unsafe-output safeguards and human approval | `GATE/SAFE`, `REVIEW_PENDING`, `UI/DEC`, `APPROVAL/APPR` and atomic-decision design | **PASS — design coverage; identity/CAS NOT VERIFIED** |
| 10. Traces, agent/E2E evaluation and regression | `EVAL/FIX`, standalone TEST, `EVENTS/TRACE/STORE` and tests for benign/denials | **PASS — design coverage; outcome measurement NOT VERIFIED** |

## 5. Cross-diagram contract matrix

| P2-A1 component(s) | P2-A2 representation | Contract upheld |
|---|---|---|
| `OUT` and `IN` | `POL` | **One** gateway implementing dispatch, receipts, reviewer lookup and filtering; identities/scopes/schema enforced at each access |
| `CARD` + `DEP` | `ANA` | Typed card assembly and separately linked actor-removal reruns |
| `GATE` | `SAFE` | Trusted deterministic safety, provenance and candidate review-release gates |
| `APPROVAL` | `APPR` | Trusted local human-origin-only action, persisted candidate/gate checks, atomic status+decision record |
| `STATE` | `STORE` state function | Run types, parent IDs, limits, statuses and `REVIEW_PENDING` |
| `EVENTS` + `TRACE` | `STORE` event/trace functions | Trusted event capture, correlation and read-only evaluation evidence |
| `DECISION` | `STORE` decision function | One atomic candidate-state plus decision audit transaction |
| `ORCH`, `CAT`, `REV`, `EVAL` | Same identifiers | Same logical responsibilities, no additional implementation |
| `LOAD`, `MO`, `REF` | `CAT` trusted helper scope accessed through `POL` | A2 folds trusted loader/read-only helpers into catalogue participant; reviewer does not receive direct catalogue access |
| `FIX` | TEST fixture inputs to `EVAL` | Same regression suite, separate from candidate approval |

All collapses are *diagrammatic* aliases. A2's `POL→CAT` does **not** authorise all read operations; exact reviewer IDs/purpose scopes and helper filtering are part of that contract.

## 6. Mandatory checks (classification and evidence)

| # | Gate | Classification | Evidence and what it does **not** prove |
|---|---|---|---|
| 1 | Actual Mermaid syntax parser / native renderer | **NOT VERIFIED** | No working Mermaid CLI; browser automation returned `ERR_BLOCKED_BY_ADMINISTRATOR`. Structural grammar parser accepted the supported A1/A2 declarations, directed edges, frames and source message syntax; **not equivalent** to native Mermaid parse. Open the `.mmd` files in Mermaid Live / Mermaid CLI before final submission. |
| 2 | Undefined A1 node IDs and A2 participant references | **PASS** | Independent Python source parser resolved all 35 A1 node IDs, 66 directed edges and 14 sequence participants; no unknown endpoints. |
| 3 | Balanced sequence frames | **PASS** | Stack parser found 14 balanced frames: 9 `alt`, 2 `loop`, 2 `opt`, 1 `break`; 6 ordered phases, no unterminated frames. |
| 4 | Actor-to-actor messages remain mediated | **PASS (static)** | No `TA/PA/EA→different TA/PA/EA` edges or directional interactions; only `POL` dispatch/receipt and local actor self-invocations. Not an actual network isolation test. |
| 5 | Agents have no approval-state write paths | **PASS (static)** | A1 forbids simulated actors, REV and EVAL→`STATE/APPROVAL/DECISION` direct writes; A2 has no `TA/PA/EA/REV/ANA/EVAL→APPR` message. Only human UI invokes APPR; code-level RBAC remains untested. |
| 6 | CF and TEST runs cannot recurse unboundedly | **PASS (documented contract); NOT VERIFIED runtime** | Run kinds, candidate-only CF, required parent+removed actor, depth-one, no TEST recursion, fixed fixture count and aggregate lineage budget in both notes and diagram labels. No code implementing these invariants was executed. |
| 7 | All ten Part 2 requirements represented | **PASS (architecture only)** | Section 4 maps each assessment item to v3 nodes, messages, controls and note sections. Not a pass for Part 2C implementation. |
| 8 | Every exported SVG and PNG opens | **PASS** | Python XML parser successfully read detailed/overview/sequence SVG; PIL `verify()` and second open succeeded for the three primary PNGs and six phase PNGs. Dimension checks and SHA-256s recorded in JSON. |
| 9 | Rendered labels, arrows, conditions and six phase headings match Mermaid sources | **PASS (offline reconstruction); NOT VERIFIED native fidelity** | A1: exact node and edge ID multisets plus **all visible node labels** compared with source; same test for overview. A2: 100 `data-seq` SVG arrow groups each preserve exact source message, endpoints and visible label; 14 frame labels/kinds match; six phase headings present. Layout differs from Mermaid's native engine; full graphical arrow-routing/clip inspection is necessarily limited by density. |
| 10 | No unsupported implementation or real-world fraud claims | **PASS (documentary audit)** | Sources explicitly label annex data as illustrative/unverified, classify model output as hypothesis, scope approval to investigation, state mock limitations and avoid assertions of tested security, deployed identity or real wrongdoing. The report likewise reserves runtime correctness. |

No mandatory static gate **failed** in the source-derived parser and renderer checks; however **native Mermaid syntax/render and runtime functionality have not been verified**. For a defensible full assessment, these are outstanding gates rather than implied successes.

## 7. Corrected source→render manifest and image dimensions

The machine-readable `P2_A_Source_to_Render_Manifest_v3.json` records exact names, SHA-256 digests, byte sizes and dimensions of **all 12 supplied baseline source/export images and 15 produced v3 diagram/render outputs**. The numbers below were read from actual attached/output file headers, not inferred from filenames.

| Artefact | Dimensions / metadata | Rendering provenance |
|---|---|---|
| v2 A1 PNG | **2048 × 913 px** | Supplied image |
| v2 A1 SVG | `3777pt × 1685pt`; `viewBox 3777.32 × 1684.76` | Supplied offline Graphviz SVG |
| v2 A2 PNG | **921 × 2047 px** | Supplied image, **not** 3569×7933 |
| v2 A2 SVG | **3569 × 7933** declared SVG coordinates | Supplied custom offline SVG |
| v3 A1 detailed PNG | **11333 × 2313 px** | Graphviz DOT layout source-derived from v3 Mermaid; high-resolution raster |
| v3 A1 detailed SVG | `10033pt × 2048pt`; `viewBox 10032.50 × 2048.00` | Offline Graphviz converter; fully scalable |
| v3 A1 executive PNG | **6520 × 4680 px** | Graphviz conversion of separate v3 executive Mermaid |
| v3 A1 executive SVG | `1956pt × 1404pt`; `viewBox 1956 × 1403.50` | Offline Graphviz converter |
| v3 A2 full SVG + PNG | **4506 × 8668** SVG coordinates and PNG pixels | Source-driven custom sequence reconstruction; not native Mermaid |
| v3 A2 phase PNGs 1–3 | **4506 × 1225**, **4506 × 2627**, **4506 × 1204 px** | Full SVG-derived crops with repeated header/lane keys |
| v3 A2 phase PNGs 4–6 | **4506 × 1780**, **4506 × 1690**, **4506 × 1045 px** | Full SVG-derived crops with repeated header/lane keys |

**Interpretation:** SVG declared `pt` sizes and raw `viewBox` coordinates are not PNG dimensions. Raster sizes were measured independently with Pillow. The detailed A1 is a deliberately large *technical* view and remains crowded at fit-to-window scale. Use its scalable SVG at zoom and the more compact-in-content executive overview for initial communication. Six phase PNGs were specifically generated to avoid presenting a 100-message sequence as an illegible single thumbnail.

## 8. Outstanding assumptions, design dependencies and limitations

1. **Only the assignment input is a source.** The MO library is illustrative, Annex B accounts are unverified exercise excerpts and the benign S5 case must not be labelled fraud. The actual SWDA data policy, real grants transaction schema, claimant identities and production MO inventory were not supplied and are not inferred.
2. **Independent source manifest must exist.** The v3 text specifies trusted expected digest comparison, but no trusted manifest was supplied or created; therefore file-integrity enforcement has *not* been exercised. Release packaging/trust distribution must be specified in code before claiming integrity.
3. **Policy and message contracts require implementation.** A schema/ACL described on a diagram does not prove a denied recipient, injected instruction, stale state or retry remains restricted under real execution.
4. **Budget values are proposals.** 3 cards, 3 CF/candidate, 12 fixtures, 4 rounds, 12 actor turns/run, 2 schema retries, 120 seconds, 48 mock calls per CANDIDATE lineage, 12 calls per TEST fixture and 60 per suite are **configurable draft defaults**, not production measurements.
5. **Reviewer identity is local PoC assurance only.** The diagram provides no enterprise IdP, OAuth, MFA, production audit integrity or privileged-admin protection. SQLite CAS, unique constraint, transactional decision audit and concurrent conflicts must be tested with real code.
6. **Counterfactuals do not establish causation.** Fresh-context reduced runs may be nondeterministic if a future model is substituted. In this scripted PoC they demonstrate *structural simulation dependency*, not factual actor involvement or new real-world fraud strategies.
7. **Pattern and safety quality remain unmeasured.** Real-model evaluation needs privacy-preserving data, domain-reviewer agreement, blinded assessment, benign false-positive controls, calibration and adversarial benchmarks; none was executed.
8. **Native Mermaid final-publication check is outstanding.** Validate both edited `.mmd` sources and the executive overview using a native Mermaid CLI/renderer in an unrestricted environment. In particular, verify nested trust boxes, link styles and sequence label layout; replace offline derivatives with native exports if the submission specifically requires them.
9. **Part 2A is architecture only.** The assessment separately calls for Part 2B design note and **Part 2C runnable, tested coding exercise**. This patch cannot substitute for that implementation or for actual execution traces/sample pattern cards.

## 9. Recommended final acceptance gates

Before marking the whole submission “implementation passed”, an independent engineer should (a) run Mermaid CLI parsing/rendering for all three Mermaid sources; (b) use programmatic image checks to validate native SVG/PNG output; (c) execute the mock orchestration, denied-message and malicious-annex fixtures; (d) test CF taint exclusion and TEST/CF recursion caps; (e) test source digest mismatch and manifest tampering; (f) exercise concurrent SQLite reviewer decisions and forced commit failures; and (g) inspect representative simulation cards to ensure no factual fraud allegations or actionable fraud instructions appear. **None of these runtime tests is claimed completed here.**

### Final board decision

**CONDITIONAL PASS for Part 2A targeted architectural patch.** The requested design clarifications, references, actor profiles, lineage restrictions, render-size correction, source-to-render traceability and cross-diagram mappings are represented, with no required Part 2 architectural capability removed. The remaining conditions are **native Mermaid verification, executable policy/approval tests and evaluation evidence**, which belong to subsequent validation and Part 2C implementation.
