---
name: p7-code
description: "P7 platform coding conventions for all 5 layers. Use when: implementing features, writing code, creating new files, adding endpoints, or reviewing code on the P7 platform across Frontend, Middleware, Pricing Engine, CMDB, or PEDB."
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
