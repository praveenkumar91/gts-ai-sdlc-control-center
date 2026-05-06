---
name: t7-code
description: "T7 Trading System coding conventions for all 4 layers. Use when: implementing T7 features, writing code, creating new files, adding endpoints, reviewing code on the T7 platform across Core Engine (C++17), Gateway (Java 17), Admin UI (Angular), or Database (Oracle)."
systems: [t7]
---

# T7 Code — Platform Coding Standards

All T7 implementation work MUST follow these conventions. Match surrounding code style exactly. Use existing imports and utilities before creating new ones.

## T7 Layer Table

| Layer | Path | Language | Build Command |
|-------|------|----------|---------------|
| Core Engine | `gts.t7.core/` | C++17 (CMake) | `cmake --build . --config Release` |
| Gateway | `gts.t7.gateway/` | Java 17 (Maven/Spring Boot) | `mvn clean package` |
| Admin UI | `gts.t7.admin/` | Angular/TypeScript | `ng build --prod` |
| Database | `gts.t7.database/` | SQL (Oracle) | SQL scripts via `sqlplus` |

---

## Core Engine Conventions (C++17)

### Performance
- RAII throughout — every resource acquisition is a construction
- **No exceptions in the hot path** — use error codes (`enum class ErrorCode`) or `std::expected<T, E>` for expected failure paths
- Lock-free data structures preferred in order matching: `std::atomic`, `folly::MPMCQueue`, or custom ring buffers
- No dynamic allocation (`new` / `malloc`) inside the matching engine per-order path — use pre-allocated object pools

### Structure
- File naming: `PascalCase.cpp` / `PascalCase.hpp`, one primary class per file
- Method naming: `camelCase`; class naming: `PascalCase`; constants: `UPPER_SNAKE_CASE`
- New REST endpoints: add paired `.cpp/.hpp` in `src/rest/`, register handler in `RestHandler`
- New matching logic: extend `src/matching/` — follow the `MatchingEngine` base class interface

### Testing
- Google Test in `gts.t7.core/test/`
- Performance benchmarks: Google Benchmark in `gts.t7.core/bench/`
- Build tests: `cmake --build . --target tests && ctest`

---

## Gateway Conventions (Java 17)

### Framework
- Spring Boot — use `@Service`, `@RestController`, `@Component`
- Constructor injection only — never `@Autowired` on fields

### FIX Protocol (QuickFIX/J)
- Implement `quickfix.Application` interface for session callbacks: `onMessage`, `toApp`, `fromApp`, `onCreate`, `onLogon`, `onLogout`
- FIX message fields: use `quickfix.field.*` constants, never raw tag integers
- FIX session config: `gts.t7.gateway/src/main/resources/quickfix.cfg`
- Common message types: `NewOrderSingle (D)`, `OrderCancelRequest (F)`, `OrderCancelReplaceRequest (G)`, `ExecutionReport (8)`, `OrderCancelReject (9)`

### Async Processing
- `CompletableFuture` for non-blocking order routing downstream to Core Engine
- Do NOT block gateway threads — order acknowledgement is async
- Backpressure: use bounded queues (`LinkedBlockingQueue` with capacity) before Core Engine IPC

### Logging & Config
- SLF4J: `log.info/warn/debug/error` — never `System.out.println`
- Config: `application.properties` / `application.yml` — never hardcode connection strings, ports, or FIX session parameters
- Secrets: inject via environment variables or Spring Cloud Config

### Testing
- JUnit 5 + Mockito in `src/test/java/`
- Integration tests: `@SpringBootTest` with in-memory H2 where Oracle is not needed
- Build: `mvn test`

---

## Admin UI Conventions (Angular/TypeScript)

### State Management (NgRx)
- Actions: `store/actions/*.actions.ts` — use `createAction` with `props<>()`
- Reducers: `store/reducers/*.reducer.ts` — pure functions, immutable state updates
- Selectors: `store/selectors/*.selectors.ts` — use `createSelector` for derived state
- Effects: `store/effects/*.effects.ts` — side effects only (HTTP calls, WebSocket events)
- Never mutate state directly — always return new objects/arrays in reducers

### HTTP & Observables
- Angular `HttpClient` injected via constructor — never `fetch()`
- API base URLs: `environment.ts` (dev) and `environment.prod.ts` (prod) — never hardcode
- RxJS: use `async` pipe in templates; manage subscriptions with `takeUntil(this.destroy$)` pattern or `AsyncPipe`
- Unsubscribe on destroy: implement `OnDestroy` with `private destroy$ = new Subject<void>()`

### Forms
- Reactive forms only: `FormBuilder`, `FormGroup`, `FormControl`
- Validation: built-in `Validators.*` + custom validator functions — no template-driven `ngModel`

### Component Rules
- Selector naming: `app-kebab-case`; class naming: `PascalCaseComponent`
- `ChangeDetectionStrategy.OnPush` on all components receiving store data
- No `console.log` — use `inject(LoggerService)` or remove debug statements entirely

### Testing
- Jest + Angular Testing Library (`*.spec.ts` alongside each component/service)
- Run: `ng test --watch=false`

---

## Database Conventions (Oracle)

### Schema Changes
- Migration scripts: `gts.t7.database/migrations/V{version}__{description}.sql`
- Always migration-safe: `ALTER TABLE` — never `DROP TABLE` + `CREATE TABLE`
- Every migration file must have a paired rollback script: `gts.t7.database/rollbacks/V{version}__rollback.sql`

### Primary Keys & Sequences
- Use Oracle `SEQUENCE` objects — `seq_{table_name}.NEXTVAL` as default
- Never rely on `ROWNUM` or `ROWID` as stable identifiers

### Stored Procedures
- Complex multi-step queries and order history aggregations: Oracle stored procedures in `gts.t7.database/procedures/`
- Naming: `pkg_{domain}.proc_{action}` (e.g. `pkg_orders.proc_get_history`)

### Partitioning
- High-volume tables (order history, execution reports): partition by `RANGE` on `ORDER_DATE`
- Instrument-specific data: consider `LIST` partitioning on `INSTRUMENT_TYPE`

### Data Seeds
- No DML in migration files — data seeds go in `gts.t7.database/data/`

---

## T7 Data Flow

```
Admin UI (Angular)
    │  REST (HTTP/S) — order management, reference data
    ▼
Gateway (Java / Spring Boot)
    │  FIX protocol (QuickFIX/J) — order entry & execution reports
    │  REST internal API — admin commands
    ▼
Core Engine (C++17)
    │  Shared memory / UNIX domain socket — low-latency order routing
    ▼
Exchange Matching Engine
    │  ITCH (market data out) / OUCH (order entry in)
    ▼
Market Data Feed → Gateway → Admin UI (via WebSocket / SSE)
```

- Admin UI sends order management actions over REST to the Gateway
- Gateway translates REST calls into FIX messages and routes to Core Engine
- Core Engine communicates with the matching engine via shared memory or UNIX domain socket
- Market data flows back via ITCH feed → Gateway parses → Admin UI receives via WebSocket

---

## Commit Scope Format

Use layer-specific scopes for Conventional Commits:

| Scope | Layer |
|-------|-------|
| `feat(core):` | Core Engine C++ changes |
| `feat(gateway):` | Java Gateway changes |
| `feat(admin):` | Angular Admin UI changes |
| `feat(db):` | Database schema, procedure, or data changes |

Multi-layer commits: use the primary changed layer as scope and list all layers in the commit body.

---

## General Rules

- Match surrounding code style exactly — no style improvements beyond the task scope
- Handle errors at system boundaries only — do not add defensive error handling deep inside utilities
- No `console.log` / `System.out.println` anywhere across any layer
- No placeholder code: no "TODO", "implement later", or stub functions left disconnected
- No hardcoded secrets, URLs, or connection parameters in any layer
