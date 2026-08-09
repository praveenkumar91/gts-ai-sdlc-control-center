---
name: p7-code
description: "P7 platform coding conventions and change-localisation for all 5 layers. Use when: implementing features, writing code, creating new files, adding endpoints, reviewing code, or locating the exact files a change must touch on the P7 platform across Frontend, Middleware, Pricing Engine, CMDB, or PEDB."
systems: [p7]
---

# P7 Code — Platform Coding Standards

All P7 implementation work MUST follow these conventions. Match surrounding code style exactly. Use existing imports and utilities before creating new ones.

## P7 Layer Table

| Layer | Path | Language | Build Command |
|-------|------|----------|---------------|
| Frontend | `gts.p7.frontend/` | React/TypeScript (Vite) | `npm run build` |
| Middleware | `middleware/` | Node.js/Express | `node -e "require('./src/index.js')"` |
| Pricing Engine | `gts.p7.pricingengine/` | C++17 (CMake/Crow) | `cmake .. && make -j4` |
| CMDB | `gts.p7.common.controller-monitor.database/commondb/` | SQL (MySQL) | SQL scripts |
| PEDB | `gts.p7.pricingengine/sql/schema/` | SQL (MySQL) | SQL scripts |

---

## P7 Repository Map (org `dev` on `github.deutsche-boerse.de` — verified)

The layer table above uses **working-tree paths** (the conventional checkout directory). Each maps to a **git repo** — and that repo name is what the `github` skill and `gts-build-graph` (component `p7/<x>` → repo `gts.p7.<x>`) actually use. The Pricing Engine is **more than one repo**:

| Working path | Git repo | Role | Language |
|---|---|---|---|
| `gts.p7.pricingengine/` | `gts.p7.pricingengine` | Main Pricing Engine — data ingest (EMDI / Refinitiv / MDH / CIL over multicast/WS/AMQP), order book, **vola fitting waterfall**, REST (Crow) / WebSocket / AMQP, orchestration; `app/OptionsCalculations` (Black-Scholes / Black76) | C++ |
| *(linked by the PE)* | **`gts.p7.pricer`** | **The option pricers + greeks / rate math** — `pricer/Pricer.cxx` (analytic), `BinomialPricer.cxx`, `PricerCalculations.cxx`, `PricerUtils.cxx`, `RateInterpolation.cxx`. **A pricing-formula bug (delta / vega / vola / rate) localises HERE, not in `pricingengine`.** | C++ |
| *(linked by the PE)* | `gts.p7.dataaccess.common` | Shared data-access library used by the PE | C++ |
| `gts.p7.frontend/` | `gts.p7.frontend` | React / TypeScript UI | TypeScript |
| `middleware/` | `gts.p7.middleware` | Node.js / Express middleware (`src/routes/api/`, Socket.IO ↔ Faye) | JavaScript |
| — | `gts.release.p7` | Controls P7 builds & releases (baseline, the `release/p7` aggregate) | — |
| — | `gts.p7.doc` | P7 documentation | — |

> **Localisation consequence (grounded in SIR P7-2955):** the delta-effective `vola`→`vega` fix was in `gts.p7.pricer/pricer/Pricer.cxx#L111` — a repo the layer table does not surface. So route a **pricing / greeks / rate formula** symptom to `gts.p7.pricer` (analytic `Pricer.cxx` + `BinomialPricer.cxx`), and **data-ingest / order-book / vola-fitting / REST-WS-AMQP / orchestration** to `gts.p7.pricingengine`. `gts.p7.pricer` and `gts.p7.dataaccess.common` each carry their own `module-info.xml`, so a change there has PE-wide blast radius — check dependents via `gts-build-graph` (`system=p7`).

---

## File-Localisation Playbook — from requirement/symptom to the exact file set

> **The highest-value navigation output.** Planner, developer, tester and reviewer all depend on naming the *exact* files a change must touch — the single biggest driver of a correct plan or fix. Optimise for **both** precision (no wrong/fabricated file) **and** recall (no missing coordinated file). Localise to the **fix locus**, not the symptom.

**P7 has no code-index MCP** (unlike T7's `t7codebase`). Localisation is done with the agent's own **`read`/`search`** over the working tree, the **`p7-spec`** skill as the business→code Rosetta bridge, and the **`github`** skill for cross-repo history. Precision comes from *reading* the file, not from an index.

**Input**: a requirement or bug symptom (+ any symbols, log lines, ticket text, DFS label).
**Output**: a **ranked, evidence-tagged file set** — each file with a role (impl / header / call-site / test / schema / build-config), a tag `[confirmed | likely | candidate | new-planned]`, and the evidence that proves it.

0. **Identify the P7 layer(s)** from the Layer Table above — Frontend / Middleware / Pricing Engine / CMDB / PEDB. Every path below is under that layer's root.
1. **Translate business → code vocabulary first — via the `p7-spec` skill.** The symptom is *business* language; the code uses different identifiers, and raw grep of a business phrase misfires. Run the symptom through `p7-spec` (`search` / `grep` — see that skill's index-status note) so the DFS/DTS restates it in **canonical P7 vocabulary** and names the concept + parameters. Harvest those canonical nouns + named symbols as your **code-search terms**. *(e.g. "vol curve won't fit at the wings" → DFS11120 → `VolaFittingWaterfall` / `verticalFit` / `parallelShift` / Akima — search PE code for those, not "wings".)*
2. **Find where the behaviour is defined — iterate; never single-shot.** Seed `search` with the most concrete identifiers you have (exact class / function / REST route / Socket.IO event / config key / log macro ID / error string), scoped to the layer path. Read the top hits; if they are only *near* the locus, extract the real symbols they use and re-search. For the Pricing Engine, the **Key Singletons**, **Important PE Files**, and data-flow tables in this skill name the usual loci (`DataAccess`, `OrderBookBuilder`, `OptionsCalculations`, `VolaFittingWaterfall`, `CrowHandler`, `library/gen/`) — **and for a pricing / greeks / rate formula, the `gts.p7.pricer` repo (`Pricer.cxx` / `BinomialPricer.cxx`), per the Repository Map above.** Exit only when you have **read** the candidate and confirmed it *decides* the behaviour. Try ≥3 term variants before concluding NOT_FOUND.
3. **Trace to the root cause, not the symptom** — the file that *emits* a symptom (a `PRINTE` log, a REST error, a wrong price) is often not the one to change. Follow the data path back (e.g. Socket.IO event → middleware Faye handler → PE WebSocket push → the computation) to where the behaviour is actually decided.
4. **Fan out to every coordinated file** — a real P7 change rarely touches one file. Use the **P7 Data Flow** chain and the **New View Checklist (12 Steps)** below as the coordination map:

   | Coordinated file | How to find it |
   |---|---|
   | Header ↔ impl pair (`.hxx` ↔ `.cxx`) | `search` the basename in the PE `app/` tree |
   | **Generated accessor** (`library/gen/*Gen.hxx/.cxx`) when a PEDB table/column changes | regen via the template in `tool/templates` — **never edit `library/gen` directly** |
   | Cross-layer fan-out of a new PE datum | PEDB schema → `library/gen` regen → `DataAccess` → REST endpoint (`app/RestEndPoints/`) + `CrowHandler` → middleware route (`src/routes/api/`) → Socket.IO event → frontend `useBroadcastStore` slice → grid |
   | **Call sites** of a changed symbol/signature | `search` the symbol across the layer; enumerate all when a public interface/REST contract/Socket.IO event changes |
   | **Test file(s)** | Frontend Jest under `src/tests/` mirroring source; PE `test/testRestAPI.py` (REST) + `P7GoogleTests` / `test*.cxx` (unit) |
   | **Schema / config / data** | PEDB `sql/schema/`, CMDB `commondb/`, `configEnv/*.env`, PE `*Config.xml` |

5. **Corroborate with change history (high-signal)** — when the **`github`** skill is available, inspect recent merged PRs/commits on the affected repo (`gts.p7.pricingengine`, `gts.p7.frontend`, `middleware`, …): files that *historically change together* with your locus are strong candidates you would otherwise miss (evidence, not proof). If `github` is unavailable, record `history: skipped`.
6. **Rank, tag, justify** — per file emit `path · role · tag · proving evidence`. **Every tag requires a path you actually opened:**
   - **[confirmed]** = you read it **and** it is the fix locus.
   - **[likely]** = you read it **and** it is coordinated by a verified rule (header↔impl pair, direct caller, matching test, a 12-step fan-out step).
   - **[candidate]** = path **verified to exist** but relevance uncertain → developer to confirm.
   - **[new-planned]** = file does **not** exist yet; its **parent directory and naming convention are verified** (you listed the analogous files) and its creation is justified by an acceptance criterion.

   **Never tag an unverified or guessed path.** If a path can't be verified, don't list it as a file — record it as a **discovery / risk item** with the search strategies tried. Prefer a well-reasoned superset over dropping a real file; never invent a path.

### Search Quality Rules
- Try at least **three** distinct search strategies (class → method → related enum/route/event) before concluding a symbol is NOT_FOUND.
- Too many hits → narrow by adding the layer path or component name; nothing → broaden via a canonical term from `p7-spec` or a P7 naming convention (`divident`, `volas`, suffix `S`/`E`/`I`/`Gen`).
- Always read the **surrounding context** of a match — never act on a single line in isolation.

---

## Frontend Conventions (React/TypeScript)

### Zustand
- Slice pattern: `StateCreator<MyState, [], [], SliceType>`
- Register every new slice in `useStore.tsx`
- `useShallow()` ALWAYS on object and array selectors — missing it causes infinite re-renders
- Never use local component state for real-time data — use `useBroadcastStore`

### Services
- Plain objects with async methods using `axiosApi` from `constants/axiosApi.tsx`
- API URLs: add new keys to `constants/urlConfig.tsx`, never hardcode URLs

### AG Grid
- Use utilities from `ag-grid/gridCommons.tsx`
- Register new grid IDs in `GridIds.tsx`
- Apply `memo()` to every grid view component

### Real-Time Data
- Real-time updates flow via `useBroadcastStore`, NOT component state
- No `refetchOnWindowFocus` — data is pushed via WebSocket, not refetched on focus

### Naming
- Preserve intentional P7 terminology: `divident` (not "dividend"), `volas` (not "volatilities")
- No `console.log` — no logging utility exists on the frontend; remove debug logs entirely

---

## Middleware Conventions (Node.js)

- **Module system**: CommonJS only — `require()` / `module.exports`. Never use ES `import`
- **Logger**: Winston — `logger.info/warn/debug/error`. Never `console.log`
- **Routes**: Express routes live in `src/routes/api/`
- **WebSocket handlers**: Follow patterns in `pricingEngineWebSocketHandlers.js`
- **Config**: `process.env.*` sourced from `configEnv/*.env` — never hardcode config values
- Socket.IO event names must match PE emit channel names exactly (both ends must agree)

---

## Pricing Engine Conventions (C++17)

For language-level C++ naming, formatting, and Sonar rules, refer to the `coding-guidelines` common skill. P7-specific conventions below take precedence where they conflict.

### What the PE Does

The **P7 Pricing Engine** is a high-performance C++ options/futures theoretical pricing service that replaces the legacy Sol3 software in Deutsche Börse's Eurex trading infrastructure. It receives real-time market data from multiple sources, maintains order books, fits volatility surfaces, and exposes theoretical prices via a REST API (Crow), WebSockets, and AMQP.

**Port convention**: REST API binds to port `1<env>10` (e.g. env `001` → port `10110`, env `015` → port `10150`).

### Data Sources

| Source | Transport | What It Provides |
|--------|-----------|-----------------|
| **EMDI** | Multicast | Real-time order book incremental updates (`SocketReceiver → OrderBookBuilder`) |
| **Refinitiv** | WebSocket | Interest rates and rate curves (`RefinitivReceiver → InterestRates / RateCurve`) |
| **MDH** | AMQP | Settlement prices and closing prices (`MdhReceiver → SettlementPrice / ClosingPrice`) |
| **T7 / CIL** | AMQP | Open interest (`CILReceiver → OpenInterest`) |

### PE Architecture & Data Flow

```
EMDI (multicast) → SocketReceiver → OrderBookBuilder
Refinitiv (WS)   → RefinitivReceiver → InterestRates / RateCurve
MDH (AMQP)       → MdhReceiver → SettlementPrice / ClosingPrice
T7 / CIL (AMQP)  → CILReceiver → OpenInterest

         ↓
DataAccess (singleton, shared_mutex-protected cache)
         ↓
OptionsCalculations / FuturesPricing  (QuantLib Black-Scholes / Black76)
         ↓
VolaFittingWaterfall → fullFit / verticalFit / parallelShift
         ↓
ComputedDataAccess (AkimaPoints, ImpliedVolas)
         ↓
CrowHandler (REST)  ·  MdhSender (AMQP protobuf)  ·  T7Sender
```

### Key Singletons

| Singleton | Purpose |
|-----------|---------|
| `DataAccess` | All reference/market data from pedb (instruments, products, rates, dividends). Thread-safe via `SharedMutex`. |
| `ComputedDataAccess` | Computed vola surfaces (`AkimaPoints`), implied vola containers. |
| `PricingEngineLib` | Global state: MySQL connection, log facility ID, business dates, Crow app instance. |
| `ProductStateManager` | Product/security trading state transitions. |

`DataAccess` and `ComputedDataAccess` both support session-scoped "what-if" instances (keyed by `WhatIfSessionId`) for sandbox calculations without affecting live data.

### Build

```bash
mkdir obj-debug && cd obj-debug
cmake ..
make -j 4
```

The main binary is `obj-debug/bin/pricingengine`.

Run outside an environment (no config file required):
```bash
./obj-debug/bin/pricingengine --data-log-file=/tmp/pedatalog.log
```

Run with env config (binds to port `1<env>10`):
```bash
./obj-debug/bin/pricingengine \
  --data-log-file=/opt/gts/envs/001/tmp/PricingEngine-1_001_datalog.log \
  --pe-config=/opt/gts/envs/001/opt/gts/etc/pricingEngine/PricingEngine-1_001_PricingEngineConfig.xml \
  --pedb-config=/opt/gts/envs/001/opt/gts/etc/pricingEngine/PricingEngine-1_001_PedbConnectionParams.xml
```

The `pe.sh` script wraps this for inside/outside env invocations:
```bash
./pe.sh <instance> [<envNo>]   # e.g. ./pe.sh 1 015
```

### Config File Paths

| Config | Path Pattern |
|--------|-------------|
| PE Config | `/opt/gts/envs/<env>/opt/gts/etc/pricingEngine/PricingEngine-1_<env>_PricingEngineConfig.xml` |
| PEDB Connection | `/opt/gts/envs/<env>/opt/gts/etc/pricingEngine/PricingEngine-1_<env>_PedbConnectionParams.xml` |

### Tests

**Setup (once per dev environment)**:
```bash
python3 -m venv debug_env_python3x
source debug_env_python3x/bin/activate   # bash
# or: source debug_env_python3x/bin/activate.fish
pip3 install -r test/requirements.txt
```

**Full test suite** (rebuilds binary, runs C++ unit tests, REST API tests, numeric benchmarks):
```bash
python3 test/testWrapper.py --env=006 --root=$(pwd)
```

`testWrapper.py` flags: `--skip-unit-tests`, `--skip-rest-tests`, `--skip-results-tests`, `--skip-rebuild`, `--test-filter=<pattern>`

**Run C++ unit test binaries directly**:
```bash
obj-debug/bin/P7GoogleTests                              # all Google Tests
obj-debug/bin/P7GoogleTests --gtest_filter=P7OrderBook*  # filter by name
obj-debug/bin/testLib
obj-debug/bin/testQuantLib
obj-debug/bin/testFESXPricing
```

**Integration test workflow**:
```bash
python3 test/reset_pedb.py --env 6    # reset pedb to dev sample data
# start pricing engine in debugger
python3 test/testResults.py --env 6   # run calculations and compare to benchmarks
```

Test benchmarks (expected outputs) live in `test/test_benchmarks/productId_*.txt`.

**Testing with fixed order book data**: pass `--load-testing-order-book-file=./dump_of_order_book.json` (and optionally `--load-testing-product-state-file=./test_product_states.json`) to load a deterministic order book from a file instead of live market data. The root-level `dump_of_order_book.json` and `order_book_*.json` files are captured snapshots for this purpose.

### gts-rebase Workflow (Building Against a Tagged Release)

Use `gts-rebase` to build the PE against a specific tagged release of the GTS platform infrastructure (e.g. when integrating with a specific env version). Follow the patterns in `CompileAndRun.MD` and use the `gts-rebase` tooling that rebases the CMake dependency graph against a specified GTS release tag before running cmake/make.

### gtsenv Tooling

Use `gtsenv` commands to manage environment instances for integration testing:

```bash
gtsenv create <envNo>   # create environment instance
gtsenv exec   <envNo>   # execute/start environment
gtsenv pkill  <envNo>   # stop environment
gtsenv remove <envNo>   # remove environment
```

### REST Endpoints

- Add paired `.cxx/.hxx` in `app/RestEndPoints/`, then register in `HandlerFactory` / `CrowHandler`
- The Crow app instance lives in `PricingEngineLib::crowApp`
- **File naming**: `PascalCase.cxx` / `PascalCase.hxx`
- **Method naming**: `camelCase`

### Data Access Patterns

- Use existing classes: `DataAccess`, `ComputedDataAccess`, `SessionDataAccess`
- Shared data is protected by `SharedMutex`. Call sites must acquire a `SharedLockToken` (read) or `UniqueLockToken` (write) before accessing `DataAccess`. Passing the token as a parameter signals the caller already holds the lock.
- Never use raw `int` for entity IDs — always use the strong-typed alias (see `TypesOfKeys.hxx`):
  ```cpp
  BOOST_STRONG_TYPEDEF(int32_t, ProductId)
  BOOST_STRONG_TYPEDEF(int64_t, T7InstrumentId)
  BOOST_STRONG_TYPEDEF(int32_t, ProductExpirationId)
  ```

### Generated Code (`library/gen/`)

Nearly every DB-backed entity is loaded via `Storage<TStruct, TId>`. Each generated `*Gen` class calls `SELECT * FROM <table>` on construction and populates `_items`. Any schema change requires regenerating the corresponding `*Gen.hxx/.cxx` pair — **do not edit generated files directly**.

### Naming Suffixes Convention

| Suffix | Meaning | Example |
|--------|---------|---------|
| `S` | Plain data struct (DB row) | `DateS`, `UnderlyingFeedDetailsS` |
| `E` | Entity / enum-like class | `ProductE`, `InstrumentE`, `ProductExpirationE` |
| `I` | Interface (pure-virtual) | `DataAccessI`, `HandlerFactoryI`, `IProductStateManager` |
| `Gen` | Code-generated DB accessor | `ProductExpirationGen`, `LegalProductGroupGen` |

### Logging

Use the GTS logging macros (included via `maininclude.hxx`). Never use `printf` or `std::cout`:
```cpp
PRINTI("message %s", value);   // INFO
PRINTW("warning %s", value);   // WARNING
PRINTE("error %s", value);     // ERROR
```

### Namespace

All application code lives in `gts::p7::pricingengine`. Convenience aliases:
```cpp
namespace pe = gts::p7::pricingengine;
typedef gts::p7::pricingengine::PricingEngineLib pelib;
```

### File Extensions

- `.hxx` / `.cxx` — all application and library C++ headers and sources
- `.hpp` — headers in `vola/include/vola/`
- `*Gen.hxx/.cxx` — machine-generated; do not edit directly

### Volatility Fitting Waterfall

`VolaFittingWaterfall` decides which fitting mode to apply:
1. **Full fit** (`fullFit`) — Akima spline across all available quotes
2. **Vertical fit** (`verticalFit`) — single-expiry spline
3. **Parallel shift** (`parallelShift`) — shifts existing curve by a constant

Selection is governed by `VolaFittingCriteriaEvaluation` (OTM/ITM/ATM quote counts and parity error thresholds from `VolaFittingWaterfallParameters` in pedb). Fitted surfaces are persisted to pedb and reloaded on startup via `FittedVolaPersistence`.

Disable/re-enable vola fitting at runtime:
```
set Defaults/PricingEngine/PricingEngineConfigDefault.disableVolaFitting=[TRUE|FALSE]
```

### WebSocket Push

Follow patterns in `TheoPriceUpdates.cxx` for pushing computed results over WebSocket.

### Tests

Add C++ unit tests in `test/` and Python REST tests alongside new endpoints. Verify every new object has matching constructor/destructor (no memory leaks).

### Important PE Files

| File | Purpose |
|------|---------|
| `app/main.cxx` | Entry point; wires all singletons and starts Crow |
| `app/PricingEngineShell.hxx/.cxx` | `BaseShellNM` subclass; handles startup/shutdown/config |
| `app/DataAccess.hxx` | Central read cache for all reference data |
| `app/OptionsCalculations.hxx/.cxx` | Black-Scholes/Black76 pricing |
| `app/VolaFittingWaterfall.hxx/.cxx` | Waterfall logic selecting vola fitting strategy |
| `app/OrderBookBuilder.hxx/.cxx` | Incremental order book maintenance |
| `library/gen/` | Auto-generated DB accessor classes (one per pedb table) |
| `vola/` | Self-contained Akima-spline vola fitting library |
| `model/model.py` | Python data model (source of truth for code generation) |
| `test/testWrapper.py` | Master test orchestrator |
| `sol3-mdh/theo/` | Sol3-format MDH protobuf definitions and sample `.gpb` data |

---

## Database Conventions (MySQL)

- **CMDB schema changes**: `gts.p7.common.controller-monitor.database/commondb/`
- **PEDB schema changes**: `gts.p7.pricingengine/sql/schema/`
- **DDL rule**: Always use migration-safe DDL — `ALTER TABLE`, never `DROP + CREATE`
- Document the rollback path for every migration
- Foreign key constraints must remain intact after all changes

---

## P7 Data Flow

```
Pricing Engine (C++)
    │  WebSocket push (Faye channel)
    ▼
Middleware (Node.js)
    │  Faye WS receiver → Socket.IO emit
    ▼
Frontend (React)
    │  Socket.IO handler → useBroadcastStore update
    ▼
Component / AG Grid (reads from store via useShallow selector)
```

- PE pushes data over a named Faye channel
- Middleware subscribes to that channel and re-emits via Socket.IO to the frontend
- Frontend receives the Socket.IO event and writes into `useBroadcastStore`
- Components read from the store — never from direct Socket.IO listeners in render logic

---

## New View Checklist (12 Steps)

When adding a new AG Grid view or page, complete all 12 steps:

1. Add grid ID to `GridIds.tsx`
2. Add API URL key(s) to `constants/urlConfig.tsx`
3. Create Zustand slice file and register in `useStore.tsx`
4. Create service object using `axiosApi`
5. Create the page component (`pages/`) — apply `memo()`
6. Create any sub-components (`component/`)
7. Add route to the router configuration
8. Add middleware Express route in `src/routes/api/`
9. Add PE REST endpoint (`.cxx/.hxx`) and register in `CrowHandler`
10. Wire up Socket.IO event name between PE → middleware → `useBroadcastStore`
11. Write Jest tests for the new slice and service
12. Write Python REST tests for the new PE endpoint

---

## Commit Scope Format

Use layer-specific scopes for Conventional Commits:

| Scope | Layer |
|-------|-------|
| `feat(frontend):` | React/TypeScript changes |
| `feat(middleware):` | Node.js/Express changes |
| `feat(pe):` | Pricing Engine C++ changes |
| `feat(db):` | Any database change |
| `feat(cmdb):` | CMDB-specific schema/data changes |
| `feat(pedb):` | PEDB-specific schema/data changes |

Multi-layer commits: use the primary changed layer as scope and list all layers in the commit body.

---

## General Rules

- Match surrounding code style exactly — no style improvements beyond the task scope
- Handle errors at system boundaries only — do not add defensive error handling deep inside utilities
- No `console.log` anywhere across any layer
- No placeholder code: no "TODO", "implement later", or stub functions left disconnected
