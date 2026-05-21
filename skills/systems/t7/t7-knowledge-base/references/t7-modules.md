# T7 Module Map

Use this reference to identify which module or subsystem is most likely responsible for
a given area of T7 behavior. This guides which search terms and file paths to prioritize.

---

## Core Trading Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| Matcher | MTR | Central matching engine — order book management, matching algorithms, price determination, order priority | `eurex/apps/matcher`, `eurex/apps/matcherexternal`, `eurex/apps/matchergwval`, `eurex/intmsg/model/matcher` | AD Trading Core (U) |
| Gateway | GW | Entry point for participant order flow — session management, ETI/FIX protocol handling, throttling | `eurex/gateway/gateway`, `eurex/gateway/common`, `eurex/gateway/gwconversion`, `eurex/intmsg/model/gateway` | AD Interface Design & Gateways (U) |
| Order and Floor Interface | OFI | Floor broker and TES (Trade Entry Service) order entry and management | `eurex/gateway/oficonversion`, `eurex/apps/trade-entry-service`, `eurex/intmsg/model/tradeentryservice` | AD Interface Design & Gateways (U) / AD Trading Prague (U) |
| Trade Entry Service | TES | Off-book trade negotiation, approval, and settlement initiation | `eurex/apps/trade-entry-service`, `eurex/apps/tesgwval`, `eurex/dataaccess/tradeentryservice`, `eurex/intmsg/model/tradeentryservice` | AD Trading Prague (U) |
| Pre-Trade Risk Server | PATE | Pre-trade risk checks — risk limits, kill switch, position tracking per business unit | `eurex/apps/pate` | AD Trading Core (U) |
| Reference Data Distribution | RDD | Instrument and product reference data distribution to internal components | `eurex/apps/reference-data-distributor`, `eurex/apps/refdata`, `eurex/apps/refdata-application`, `eurex/apps/refdata-database`, `common/refdata/core`, `common/refdata/generator` | AD Trading RDS (U) |
| Trade Feed Handler | TFH | Distribution of trade confirmations and execution reports to downstream systems | `eurex/apps/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler-internal` | AD Interface Design & Gateways (U) |
| Performance Monitor | PerfMon | System performance metrics collection and alerting | `perfmon/core`, `perfmon/capture`, `perfmon/ackstat`, `perfmon/ipasm`, `perfmon/market-data-reader`, `perfmon/monsoapproxy`, `common/perfmon` | AD OPM & Cloud Simulation (U) |
| ViewDB | ViewDB | Read-only market data views — order book snapshots, trade reports, instrument states | `eurex/dataaccess/viewdb-database`, `common/dataaccess/viewdb-database-common`, `common/dataaccess/view-service`, `eurex/specification/view-model` | AD Trading Architecture (U) |
| Risk Data Controller | RDC | Aggregates and distributes risk data across components | `common/dataaccess/rdc`, `eurex/dataaccess/rda-common`, `eurex/dataaccess/rda-outbound-bridge`, `common/dataaccess/rda-inbound-bridge`, `common/dataaccess/rda-outbound-bridge-common` | AD Trading Architecture (U) |
| Logical Data Store | LDS | Persistence layer for recoverable state across components | `eurex/apps/persistence` | AD Trading Core (U) |

---

## Protocol / Interface Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| Enhanced Trading Interface | ETI | Binary protocol for high-performance order entry (participants) | `eurex/gateway/eti`, `eurex/apps/etiasm` | AD Interface Design & Gateways (U) / AD OPM & Cloud Simulation (U) |
| FIX Gateway | FIX | FIX protocol adapter for standard market connectivity | `eurex/gateway/fix`, `eurex/gateway/fixgw`, `eurex/gateway/fixgwconversion`, `eurex/gateway/fixgw-rule_gen`, `eurex/intmsg/model/fixgw` | AD Interface Design & Gateways (U) |

---

## Infrastructure / Platform

| Component | Responsibility | Key Repositories |
|-----------|----------------|------------------|
| commondb | Central configuration DB — process topology, partition/market mapping, pool definitions | `eurex/dataaccess/commondb-database`, `eurex/dataaccess/commondb-database-conversion` |
| rdb | Reference data DB — products, instruments, markets, business units | `eurex/dataaccess/rdb-database`, `eurex/apps/refdata-database` |
| viewdb_\<marketplace\> | Per-marketplace ViewDB instance (e.g. `viewdb_eurex`, `viewdb_xetr`) | `eurex/dataaccess/viewdb-database`, `common/dataaccess/viewdb-database-common` |
| tesdb | TES last-IDs and product off-book tracking | `eurex/dataaccess/tradeentryservice` |
| patedb\<PartitionID\> | Per-partition PATE database instance | `eurex/apps/pate` |

---

## Key Structural Concepts

| Concept | Description |
|---------|-------------|
| Partition | A logical grouping of instruments processed by one Matcher instance |
| Market | A trading venue identified by MarketID and MIC (e.g. `XEUR` = Eurex derivatives, `XETR` = Xetra cash) |
| Pool | A set of partitions assigned to a physical matching server |
| Baseline | A named T7 software release (e.g. 14.0, 14.1); each baseline has its own indexed codebase instance |
| Instrument State | Lifecycle state of a tradeable instrument (e.g. ACTIVE, HALTED, KNOCK_OUT, EXPIRED) |
| Market State | Session state of a market (e.g. OPEN, END_OF_DAY, CLOSED, PREPARE, READY) |

---

## Search Guidance by Topic

| If the query is about... | Start searching in... |
|--------------------------|----------------------|
| Order matching, price calculation, priority | Matcher — search `matching`, `order_book`, `price_determination` |
| Session management, login, throttle | Gateway — search `session`, `throttle`, `logon`, `ETI` |
| TES trade lifecycle | OFI / TES — search `tes_trade`, `approval`, `negotiation` |
| Pre-trade risk, kill switch, limits | PATE — search `risk_limit`, `kill_switch`, `position` |
| Instrument/product data | RDD — search `reference_data`, `instrument_descriptor` |
| Order book snapshot, market data | ViewDB — search `viewdb`, `order_book_snapshot`, `market_data` |
| Margin, clearing | Prisma / RDC — search `margin`, `clearing`, `prisma` |
| Configuration, topology | commondb — search `partition`, `pool`, `process_config` |
