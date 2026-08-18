# 25-scenario, ten-repository Eurex-style SDLC evaluation

- Evaluation time: `2026-08-05T21:20:16.192129+00:00`
- Starting Git revision: `b46fc41a57017ff5deba05fefbde4f603294370d`
- Evaluated program orchestrator SHA-256: `4224e42ec21e9bcb67c9a222b2035861f7df715350a476561bc9f810a268e007`
- Scenarios: `25`
- Final pass: `25`
- Final fail: `0`
- Fixture: deterministic local Git origins/worktrees and synthetic test data
- Scope: control-plane behavior, not certification of Deutsche Boerse or Eurex production software

## Repository model

| Repository | Stack | Depends on |
|---|---|---|
| `product-reference-contracts` | `contracts` | none |
| `trade-entry-gateway` | `cpp` | `product-reference-contracts` |
| `pre-trade-risk` | `python` | `product-reference-contracts` |
| `matching-engine` | `cpp` | `product-reference-contracts`, `trade-entry-gateway`, `pre-trade-risk` |
| `trade-capture` | `node` | `matching-engine` |
| `market-data-publisher` | `node` | `matching-engine` |
| `clearing-adapter` | `python` | `trade-capture` |
| `margin-risk` | `python` | `clearing-adapter` |
| `member-portal-ui` | `vite-typescript` | `market-data-publisher`, `margin-risk` |
| `reconciliation-ops` | `python` | `trade-capture`, `clearing-adapter`, `margin-risk` |

## Scenario results

| ID | Change / control | Repository scope | Stage(s) | Expected | Official basis | Baseline | Final | Evidence / observed result |
|---|---|---|---|---|---|---|---|---|
| E01 | Full feature | 10/10 | INTAKE -> plan gate -> build/test -> integration -> plan closure -> PR gate | PR_APPROVED with exact-SHA evidence for ten changed repositories | Existing control-plane assurance | not captured | **PASS** | 10 unmodified runner-generated gate packets, integration vector, plan closure and 10-PR approval set |
| E02 | Bug fix | 1 changed / 8 validated | impact graph -> repository gates -> integration -> PR gate | PR_APPROVED; downstream consumers validated | Existing control-plane assurance | not captured | **PASS** | Dependency closure and single changed-repository PR |
| E03 | Bug remediation loop | margin-risk plus downstream UI/ops | FAIL -> remediation -> PASS -> integration -> PR gate | One bounded remediation cycle then PR_APPROVED | Existing control-plane assurance | not captured | **PASS** | Failed property gate retained before corrected exact-SHA evidence |
| E04 | Adversarial evidence | trade-capture | repository verification | Reject PASS envelope containing a failed required gate | Existing control-plane assurance | not captured | **PASS** | Top-level PASS with required idempotency-tests=FAIL |
| E05 | Breaking-contract negative control | 10 validation repositories | cross-repository integration | Reject PASS envelope containing a failed integration gate | Existing control-plane assurance | not captured | **PASS** | Exact commit vector with consumer-contracts=FAIL |
| E06 | Resilience bug | market-data-publisher plus member-portal-ui | FAIL -> remediation -> recovery integration -> PR gate | Recovery and convergence evidence reaches PR_APPROVED | Existing control-plane assurance | not captured | **PASS** | Sequence-continuity and snapshot-replay-convergence gates |
| E07 | Reconciliation negative control | trade capture, clearing, margin, UI and operations | cross-repository integration | Reject INCONCLUSIVE reconciliation inside PASS envelope | Existing control-plane assurance | not captured | **PASS** | Exact commit vector with reconciliation=INCONCLUSIVE |
| E08 | GUI feature with missing design | member-portal-ui | requirements/GUI evidence | BLOCKED_SPEC before implementation or snapshot invention | Existing control-plane assurance | not captured | **PASS** | Prose requirement; no approved design or reference image |
| E09 | Workspace safety | pre-trade-risk checkout | workspace preparation | Dirty checkout blocks before execution | Existing control-plane assurance | not captured | **PASS** | Untracked file in managed clone |
| E10 | Supply-chain/workspace safety | trade-entry-gateway checkout | workspace preparation | Wrong Git remote blocks checkout use | Existing control-plane assurance | not captured | **PASS** | Origin URL differs from program manifest |
| E11 | Repository governance | clearing-adapter | extension resolution | Missing required local policy blocks execution | Existing control-plane assurance | not captured | **PASS** | extensions_required=true with absent manifest |
| E12 | Extension supply-chain safety | matching-engine | extension resolution | Path traversal is rejected | Existing control-plane assurance | not captured | **PASS** | Local skill path ../outside/SKILL.md |
| E13 | Evidence freshness | pre-trade-risk | repository evidence ingestion | Stale/wrong extension digest rejected | Existing control-plane assurance | not captured | **PASS** | Expected digest 830abb765ffb... |
| E14 | Scope-integrity negative control | matching-engine (validation-only) | repository evidence -> PR planning | Reject changed validation-only repo; require replanning and new human approval | Existing control-plane assurance | not captured | **PASS** | base=f69a539ebe3c..., HEAD changed |
| E15 | PR integrity | reconciliation-ops | PR set -> human gate 2 | Reject stale PR head and requester self-approval | Existing control-plane assurance | not captured | **PASS** | Exact tested head and independent approval policy |
| E16 | ETI session resilience | trade-entry gateway and downstream lifecycle | FAIL -> remediation -> reconnect/retransmission -> PR gate | Missed-heartbeat recovery reaches PR_APPROVED | [ETI 14.1 sections 6.4 and 6.10](https://www.eurex.com/resource/blob/5032534/b34946612a479b4b9018590fc584a49a/data/T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf) | not captured | **PASS** | Heartbeat watchdog, disconnect, reconnect and recovery gates |
| E17 | Adversarial integration evidence | ETI gateway plus downstream consumers | cross-repository evidence ingestion | Reject integration evidence not bound to the persisted commit-vector digest | [ETI retransmission ranges](https://www.eurex.com/resource/blob/5032534/b34946612a479b4b9018590fc584a49a/data/T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf) | not captured | **PASS** | Exact SHAs were present but the immutable vector artifact digest was omitted |
| E18 | Market-data recovery | market-data publisher and member UI | sequence gap -> snapshot recovery -> integration -> PR gate | Recovered order book converges and reaches PR_APPROVED | [Market and Reference Data Manual section 7.4.2](https://www.eurex.com/resource/blob/5055560/c138bd262600e59a7c1018112fdeb252/data/T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf) | not captured | **PASS** | Snapshot completeness, sender change and stale-message gates |
| E19 | Post-acceptance evidence tampering | reference contracts within the 10-repository vector | durable-run verification | Verify detects changed repository evidence after it was accepted | [Reference-data start-up and intraday files](https://www.eurex.com/resource/blob/5055560/c138bd262600e59a7c1018112fdeb252/data/T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf) | not captured | **PASS** | Accepted gate result was changed from PASS to FAIL on disk |
| E20 | Release migration traceability | contracts, ETI gateway and all market-data consumers | cross-repository evidence ingestion | Reject a migration PASS gate without requirement IDs and source references | [T7 14.1 production-start requirements](https://www.eurex.com/ex-en/find/circulars/circular-5098798) | not captured | **PASS** | Gate had exact commit-vector binding but no normative source linkage |
| E21 | Unresolved EDCI completeness requirement | trade capture and reconciliation operations | repository decision ingestion | Reject BLOCKED_SPEC evidence that does not explain the normative blocker | [EDCI 14.1 purpose and history boundary](https://www.eurex.com/resource/blob/4978238/9b1a5723d93fd8bb2a4d319eaaf1a9e6/data/T7_R.14.1_Enhanced_Drop_Copy_Interface_-_Manual_Version_1.pdf) | not captured | **PASS** | EDCI includes lean orders but provides no history from before connection |
| E22 | Matching/risk feature | matching engine, pre-trade risk and downstream lifecycle | implementation -> business invariants -> integration -> PR gate | SMP boundary and synthetic exception reach PR_APPROVED | [Functional Reference section 7.6](https://www.eurex.com/resource/blob/5000130/73b31cf8fa62eeb7d9f0421d5ed07ea9/data/T7_Release_14.1_-_Functional_Reference_Version_1.pdf) | not captured | **PASS** | Same-owner, auction and synthetic cross-instrument behavior |
| E23 | Matcher/gateway failover | gateway, matcher and all downstream trade consumers | failure -> bounded remediation -> recovery integration -> PR gate | Market Reset semantics reach PR_APPROVED | [Eurex matcher/gateway failover guidance](https://www.eurex.com/ex-en/find/circulars/Eurex-Readiness-Newsflash-Incident-Handling-Matching-Engine-and-Gateway-Failover-Failure--5005792) | not captured | **PASS** | Persistent restore, transient purge and ordered reconnect gates |
| E24 | Disaster recovery | gateway, market data, operations and affected consumers | DR topology -> isolation -> reconnect -> PR gate | DR single-stream and environment-fencing flow reaches PR_APPROVED | [T7 Disaster Recovery Concept 2026](https://www.eurex.com/resource/blob/5112638/81542953c69a9f450c08ba44cd0b2c0a/data/T7_Disaster_Recovery_Concept_2026_v_1.1.pdf) | not captured | **PASS** | DR endpoints, absent EOBI Stream B, data fence and reconnect gates |
| E25 | Case-variant self-approval | member portal UI | Human Gate 2 | Reject requester identity even when reviewer casing differs | [T7 participant and user maintenance](https://www.eurex.com/resource/blob/5000084/9af4d0c2c09a4de82607115b1f146889/data/T7_R.14.1_Derivatives_Market_-_Participant_and_User_Maintenance_Manual_Version_1.pdf) | not captured | **PASS** | requested_by=feature-requester; approved_by=Feature-Requester |

## Confirmed deficiencies and corrections

| Scenario | Baseline deficiency | Correction | Final result |
|---|---|---|---|

## Stage assurance

| Stage | What this evaluation demonstrated | Remaining production requirement |
|---|---|---|
| Intake and impact | Dependency closure and execution waves across ten repositories | Curated, complete real repository graph and authoritative DFS/FSD links |
| Human Gate 1 | Digest-bound independent plan approval is mandatory | Real GitHub environment reviewers and accountable architecture/risk owners |
| Workspace | Clean checkout, expected remote, isolated branch/worktree and extension integrity | Enterprise credentials, network controls and repository onboarding |
| Repository verification | The frozen per-change matrix selects reusable gate IDs; unmodified runner evidence is exact-commit, changed-file and extension-packet bound | Native C++/Python/Node/Vite commands, approved test data and real performance environments |
| Integration | The executed cross-repository gate set and requirement/criterion/evidence mappings exactly match the approved matrix and ten-repository commit vector | Market/member simulators, contract fixtures, replay, latency, capacity and reconciliation environments |
| Plan closure | Every frozen requirement, owning repository, acceptance criterion and required evidence type must be covered; distinct independent and adversarial reviews are mandatory | Authoritative DFS/FSD completeness, accountable reviewers and approved real evidence mappings |
| GUI | Missing normative visual baseline stops at BLOCKED_SPEC | Approved design system/screens, Playwright baselines, browser matrix and accessibility owners |
| Human Gate 2 | Exact PR heads, required checks and independent reviewers are mandatory | Real CODEOWNERS, protected branches and separation-of-duties policy |
| Production | Not exercised by this local evaluation | Pre-production, migration/rollback rehearsal, business validation, production approval, canary, monitoring and post-deploy reconciliation |

## Public basis and limitations

The repository names and flows are an illustrative decomposition based only on public interface concepts. They are not a statement of Deutsche Boerse's internal architecture.

- [T7 Release 13.0 system documentation](https://www.eurex.com/ex-en/support/initiatives/t7-release13): ETI, EOBI, market/reference data, GUI and traceability boundaries.
- [T7 system overview](https://www.eurex.com/ex-en/support/technology/t7): high-throughput trading-platform context.
- [Eurex Clearing risk](https://www.eurex.com/ec-en/support/risk): clearing-risk and intraday-margin context.
- [T7 Release 14.1 ETI manual](https://www.eurex.com/resource/blob/5032534/b34946612a479b4b9018590fc584a49a/data/T7_R.14.1_Enhanced_Trading_Interface_-_Manual_Version_2.pdf): session heartbeat, recovery and retransmission behavior.
- [T7 Release 14.1 market and reference data manual](https://www.eurex.com/resource/blob/5055560/c138bd262600e59a7c1018112fdeb252/data/T7_R.14.1_%20EMDI_MDI_RDI_Manual_Version_2.pdf): snapshot recovery, sequence handling and RDI/RDF cutover.
- [T7 Release 14.1 EDCI manual](https://www.eurex.com/resource/blob/4978238/9b1a5723d93fd8bb2a4d319eaaf1a9e6/data/T7_R.14.1_Enhanced_Drop_Copy_Interface_-_Manual_Version_1.pdf): lean-order coverage and absence of historical catch-up.
- [T7 Release 14.1 functional reference](https://www.eurex.com/resource/blob/5000130/73b31cf8fa62eeb7d9f0421d5ed07ea9/data/T7_Release_14.1_-_Functional_Reference_Version_1.pdf): self-match prevention and synthetic matching constraints.
- [T7 Release 14.1 production-start circular](https://www.eurex.com/ex-en/find/circulars/circular-5098798): interface migration, key rotation and reference-data restart.
- [T7 matcher and gateway failover guidance](https://www.eurex.com/ex-en/find/circulars/Eurex-Readiness-Newsflash-Incident-Handling-Matching-Engine-and-Gateway-Failover-Failure--5005792): market reset and persistent versus non-persistent recovery.
- [T7 Disaster Recovery Concept 2026](https://www.eurex.com/resource/blob/5112638/81542953c69a9f450c08ba44cd0b2c0a/data/T7_Disaster_Recovery_Concept_2026_v_1.1.pdf): DR endpoint changes, stream availability and isolation.
- [T7 derivatives participant and user maintenance manual](https://www.eurex.com/resource/blob/5000084/9af4d0c2c09a4de82607115b1f146889/data/T7_R.14.1_Derivatives_Market_-_Participant_and_User_Maintenance_Manual_Version_1.pdf): entitlements, transaction limits and re-login semantics.

Synthetic fixtures are intentionally used only to make orchestration failures deterministic. A PASS proves that the configured controls behaved as tested; it does not prove that unspecified requirements are correct or that production software is defect-free.
