---
name: t7-refdata
description: "T7 / Eurex reference-data (RDS/RDA) lookup, valid-value sets, and spec-vs-model-vs-data conformance. Use when: checking whether an instrument / product / entity exists and its attributes; listing the valid values of an RDS enum or field; verifying that a DFS/DTS reference-data change matches the real RDS documentation model and the live reference database; grounding the 'Required Changes to RDS/RDA' chapters of a spec in real entity/attribute/enum names. Covers all interactions with the `t7dbcopy` (T7 RDS Sense) and `eurex_refdata` (Eurex GraphQL) MCP tools — agents must always delegate reference-data lookups to this skill rather than calling the MCP tools directly. Read-only."
systems: [t7]
tools: [t7dbcopy/*, eurex_refdata/*]
user-invocable: false
---

# T7 Reference Data (RDS/RDA) — lookup, valid-values & conformance

Use this skill whenever you need **live T7/Eurex reference data** — instruments, products, entities,
attributes, and enum valid-value sets — or need to **check a reference-data spec/code change against the
real reference data**. This skill governs **all** direct interactions with the `t7dbcopy` and
`eurex_refdata` MCP tools — agents must always delegate reference-data lookups to this skill rather than
calling the MCP tools directly.

> **Read-only, always.** Only ever issue `SELECT` / GraphQL *query* operations. Never propose or attempt
> an `INSERT` / `UPDATE` / `DELETE` / DDL, never mutate any reference data. The underlying store is a
> read replica; treat it as strictly read-only.

---

## 1. Two reference-data planes — do not conflate them

| Plane | MCP | What it is | Use it for |
|---|---|---|---|
| **Internal RDS** (authoritative) | `t7dbcopy` ("T7 RDS Sense") | The internal RDS **documentation model** *and* the live RDS **database copy**, **baseline-aware** (`get_deployed_version`). Also the Contract Manager model. | Entity/attribute/enum lookups, valid-value sets, and **conformance** of an in-flight DFS/DTS change |
| **Public Eurex** | `eurex_refdata` | The **public** Deutsche Börse Eurex GraphQL API (production products, contracts, trading hours, settlement prices, …). **Not** aligned to the change's target baseline. | Public product / contract / trading-hours / settlement lookups and cross-checks **only** |

> **Hard rule.** Conformance of an in-flight change uses **`t7dbcopy`** (+ `t7-spec`). Use
> `eurex_refdata` for public lookups and corroboration **only** — **never** as the conformance gate
> (it reflects production, not the change's target release).

### Three namespaces — the connector's #1 gotcha
- **RDS** = the *documentation/model* namespace (logical entities, attributes, enums).
- **`rdb`** = the *live Trading-RDS database* (the actual data). The live DB is **`rdb`, never "rds"**.
- **`comadb`** = the **Contract Manager (CoMa-RDS)** database — a **separate** model; query it with the
  `*_coma_*` tools and `database="comadb"`. Do **not** mix CoMa entities with Trading-RDS (`rdb`).

For the static component/abbreviation map (RDS/RDA/RDC/RDD/`rdb`), see the **`t7-knowledge-base`** skill;
this skill is the **live data + model** behind that map.

---

## 2. Tool selection guide

### 2a. `t7dbcopy` — T7 RDS Sense (follow this ordered workflow)

| Phase | Tool | When to use |
|---|---|---|
| **1. Discover** | `mcp_t7dbcopy_search_entities` | keyword search by entity name/description — **start here** |
| | `mcp_t7dbcopy_list_entities` · `mcp_t7dbcopy_get_baseline_stats` | browse a baseline / high-level counts |
| | `mcp_t7dbcopy_search_attributes` | find an attribute by name across **all** entities |
| **2. Understand schema** | `mcp_t7dbcopy_get_entity` | the RDS **documentation** for an entity (logical model, attributes, enums) |
| | `mcp_t7dbcopy_map_entity_to_tables` | ⭐ **always** map entity → real table first — single-table inheritance means child entities (e.g. `DerivativeInstrument`) share the parent table (`instrument`) |
| | `mcp_t7dbcopy_describe_table` · `mcp_t7dbcopy_get_table_indexes` · `mcp_t7dbcopy_get_create_table` | physical columns (incl. audit FKs not in the model) |
| | `mcp_t7dbcopy_get_entity_relations` | parent/child relationships, cascade rules |
| **3. Extract data** | `mcp_t7dbcopy_run_query` | ⭐ primary for data — JOINs, GROUP BY, COUNT, inline `map_enum('EnumType', col)`. **SELECT-only.** |
| | `mcp_t7dbcopy_query_entity` · `mcp_t7dbcopy_count_entity` | simple single-table peek / counts (no JOINs) |
| | `mcp_t7dbcopy_get_deployed_version` | which RDS release is deployed on an environment (the **baseline anchor**, §4) |
| **4. Enums** | `mcp_t7dbcopy_resolve_enum` | full enum listing from documentation, or **compare doc vs runtime** |
| | `mcp_t7dbcopy_lookup_enum` · `mcp_t7dbcopy_resolve_map_enum` | bulk dump / single-value runtime resolution |
| **5. Compare** | `mcp_t7dbcopy_diff_baselines` · `mcp_t7dbcopy_list_rds_baselines` | what changed between two RDS versions |
| **Environments** | `mcp_t7dbcopy_get_environments` · `mcp_t7dbcopy_list_databases` · `mcp_t7dbcopy_list_tables` | discover env numbers, databases (`rdb`/`comadb`), tables |
| **CoMa** | `mcp_t7dbcopy_search_coma_entities` · `list_coma_entities` · `get_coma_entity` · `get_coma_baseline_stats` · `list_coma_baselines` | Contract Manager model (`comadb`) |

Baseline shortcut: pass `"latest"` or `"previous"` instead of first calling `list_rds_baselines`.

### 2b. `eurex_refdata` — public Eurex GraphQL (typed queries)

`mcp_eurex_refdata_query_products` · `query_contracts` · `query_trading_hours` · `query_expirations` ·
`query_settlement_prices` · `query_deliverable_bonds` · `query_tes_profiles` · `query_tick_rules` ·
`query_holidays` · `query_vendor_codes` · `query_flexible_contracts` · `query_enlight` ·
`query_enlight_responders` · `query_changelog`; `mcp_eurex_refdata_graphql` (raw query, escape hatch).

---

## 3. Routing — which question goes where

| Question | Route |
|---|---|
| Instrument / product / entity exists? attributes? (internal, baseline-aware) | `t7dbcopy`: `search_entities` → `get_entity` → `map_entity_to_tables` → `run_query` |
| Valid-value set of an RDS enum/field (**model** side) | `t7dbcopy`: `resolve_enum` / `lookup_enum` |
| Valid-value set as **actually present** in data | `t7dbcopy`: `run_query` with inline `map_enum(...)` |
| CoMa product/contract reference data | `t7dbcopy`: `*_coma_*` + `run_query(database="comadb")` |
| **Public** product / contract / trading-hours / settlement / holiday facts | `eurex_refdata`: typed `query_*` |
| What the **spec** says an RDS field should be | delegate to **`t7-spec`** |
| Which release the live env is on | `t7dbcopy`: `get_deployed_version` |

---

## 4. Modes

### 4.1 Lookup
Answer entity / instrument / enum questions directly — internal via `t7dbcopy`, public via
`eurex_refdata`. Always `map_entity_to_tables` before querying a table.

### 4.2 Valid-value
Return the value set for a named RDS field/enum, labelling each line by source: **[model]**
(`resolve_enum` documentation) and/or **[data]** (`run_query` + `map_enum` runtime). Report both when
they differ.

### 4.3 Conformance (three-way, baseline-anchored) — the high-value mode

Given a DFS/DTS that changes an RDS field/attribute/enum, do **not** simply diff spec vs live data.
Do the three-way check the connector is built for:

1. **Anchor the baselines (do this first).** Record the three reference frames and **state them**:
   - **code** baseline — from `t7-code` `list_releases`;
   - **DFS/DTS target** release — from the spec;
   - **live env** — `mcp_t7dbcopy_get_deployed_version`.
   They routinely differ; never diff across mismatched baselines without saying so.
2. **Spec obligation** — via **`t7-spec`**, extract the declared valid-value set / attribute definition
   (the DFS "Required Changes to RDS/RDA" chapter, or the DTS "Changes in RDS Model").
3. **RDS documentation model** — `get_entity` / `resolve_enum` (doc side): does the model **for the
   target baseline** define the field/enum, with which values?
4. **Live data** — `run_query` + `map_enum` / `resolve_enum` (runtime side): what values actually exist
   in `rdb` on the stated env?
5. **Diff and classify — baseline-aware:**

   | Status | Meaning |
   |---|---|
   | `match` | spec = model = data |
   | `model-gap` | spec value **not** in the RDS model for the target baseline → a **real** inconsistency (actionable) |
   | `data-absent` | in spec **and** model but not yet in live data → **expected if the change is not deployed on that env** → report as *pending deployment*, **not** a defect |
   | `extra-in-data` | value in data but not in spec/model → investigate (legacy / undocumented) |

   Use `mcp_t7dbcopy_diff_baselines` to show what the model change itself is between the current and
   target RDS baseline — the most honest signal for an in-flight change.

> **The correctness crux.** The **primary** conformance is *spec ↔ RDS documentation model for the
> target baseline* (both are version-scoped and comparable). **Live data is corroboration, never the
> gate.** A value present in spec+model but absent in live data is `data-absent` (**pending
> deployment**) — never `GAPS_FOUND`. Flagging a change's own not-yet-deployed value as a defect is a
> false positive. If the baselines cannot be aligned (e.g. the target isn't in `list_rds_baselines`),
> return `INTENT_UNVERIFIABLE` rather than guessing.

---

## 5. Output contract

```markdown
## RDS Answer: <lookup | valid-values | conformance>

### Query
- Target: <instrument / entity / enum / field>
- Spec (if conformance): <DFS/DTS id + section>
- Baselines: code=<rel> · DFS target=<rel> · live env=<env>@<deployed_version>

### Result
<data / valid-value list — label each line [model] or [data]>

### Conformance (if applicable)
| Value | In Spec | In RDS Model | In Live Data | Status |
|-------|---------|--------------|--------------|--------|
| ...   | yes/no  | yes/no       | yes/no       | match / model-gap / data-absent(pending) / extra-in-data |

**Verdict:** CONFORMS | GAPS_FOUND (model-gaps only) | PENDING_DEPLOYMENT | INTENT_UNVERIFIABLE

### Sources
| Source | Details |
|--------|---------|
| t7dbcopy | <tool + entity/enum/query> |
| eurex_refdata | <typed query> (public cross-check only) |
| t7spec | <doc id + section> |
```

---

## 6. Constraints & anti-patterns

- **Read-only** — only `SELECT` / GraphQL query. Never propose or run a mutation. Query `rdb` / `comadb`
  only (the allowed databases); never invent a database name.
- **`map_entity_to_tables` first** — single-table inheritance means a child entity has no own table;
  querying the wrong table yields wrong data.
- **Facts vs interpretation** — report what the data shows; do **not** infer application logic
  (fallbacks, tiering, thresholds, inheritance) from data patterns alone. A **NULL foreign key means
  "not linked"**, not a default/wildcard. If the documentation doesn't state a behaviour, say it is
  undocumented rather than guessing.
- **No bulk extraction** — never dump full member/participant tables; prefer targeted `get_entity` /
  `describe_table` / `count_entity` / scoped `WHERE`. Reference data is internal.
- **Baseline discipline** — always state the RDS baseline / env a fact came from; a value is meaningful
  only against a specific baseline. Live data is corroboration, not the conformance gate (§4.3).
- **Do not conflate planes** — internal `t7dbcopy` (authoritative, baseline-aware) vs public
  `eurex_refdata` (production); Trading-RDS (`rdb`) vs CoMa-RDS (`comadb`).
- **Delegate, don't inline** — never call `t7dbcopy` / `eurex_refdata` MCP tools from agent
  instructions directly; all calls flow through this skill. Spec text comes from `t7-spec`, the static
  component map from `t7-knowledge-base`.
