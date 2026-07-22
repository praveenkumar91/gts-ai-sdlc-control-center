# T7 Module Map

Use this reference to identify which module or subsystem is most likely responsible for
a given area of T7 behavior. This guides which search terms and file paths to prioritize.

---

## Core Trading Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| Matcher | MTR | Central matching engine — order book management, matching algorithms, price determination, order priority | `eurex/apps/matcher`, `eurex/apps/matcherexternal`, `eurex/apps/matchergwval`, `eurex/intmsg/model/matcher` | AD Trading Core (U) |
| Gateway | GW | Entry point for participant order flow — session management, ETI/FIX protocol handling, throttling | `eurex/gateway/gateway`, `eurex/gateway/common`, `eurex/gateway/gwconversion`, `eurex/intmsg/model/gateway` | AD Interface Design & Gateways (U) |
| Outbound Feed Interface | OFI | Outbound post-trade feed — distributes the Matching Engine's (adjusted) audit-trail records (deals, trades, instrument-state changes) to downstream systems. Public output path: PATE → OFI → TFH → C7 (clearing). CMDB application name `OutboundFeedInterface` (ShortName `Ofi`). Not an order-entry interface. | `eurex/gateway/outboundfi`, `eurex/gateway/oficonversion`, `eurex/intmsg/model/outboundfi` | AD Interface Design & Gateways (U) |
| Trade Entry Service | TES | Off-book trade negotiation, approval, and settlement initiation | `eurex/apps/trade-entry-service`, `eurex/apps/tesgwval`, `eurex/dataaccess/tradeentryservice`, `eurex/intmsg/model/tradeentryservice` | AD Trading Prague (U) |
| Post Processing and Audit Trail Engine | PATE | Post-trade processing engine that consumes Matching Engine audit trail messages, creates deal and trade records, and distributes trade notifications. Successor to PoPE (Post Processing Engine) + TRAM (merged at R10.0). Public output path: OFI → TFH → C7 (clearing); private output path: GW → ETI/FIX → participants. The `patedb` database stores audit trail persistence data and Pre-Trade Risk Limit (PTRL) definitions. The *PaTe* acronym originally derived from "Post-Processing And Trade Engine" (R10.0 merge); the "Post Processing and Audit Trail Engine" expansion appears in specs from R13 onward. Repos: `eurex/apps/pate`. | `eurex/apps/pate` | AD Trading Core (U) |
| Reference Data Distribution | RDD | Instrument and product reference data distribution to internal components | `eurex/apps/reference-data-distributor`, `eurex/apps/refdata`, `eurex/apps/refdata-application`, `eurex/apps/refdata-database`, `common/refdata/core`, `common/refdata/generator` | AD Trading RDS (U) |
| Trade Feed Handler | TFH | Distribution of trade confirmations and execution reports to downstream systems | `eurex/apps/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler-internal` | AD Interface Design & Gateways (U) |
| Performance Monitor | PerfMon | System performance metrics collection and alerting | `perfmon/core`, `perfmon/capture`, `perfmon/ackstat`, `perfmon/ipasm`, `perfmon/market-data-reader`, `perfmon/monsoapproxy`, `common/perfmon` | AD OPM & Cloud Simulation (U) |
| ViewDB | ViewDB | Read-only MySQL database that materializes data from `rdb` (reference data) and `commondb` (configuration) into denormalized, GUI-consumable views — effectively mimicking materialized views. Holds `Rda*` instrument/product reference tables (e.g. `RdaInstrumentDerivatives`), `GUI*` views (TES profiles, ticker/security, volatility-strategy underlyings), contract/security statistics, and instrument/market state. Refreshed by post-processing procedures (`post_process_Rda*`) rather than being a live market-data feed. | `eurex/dataaccess/viewdb-database`, `common/dataaccess/viewdb-database-common`, `common/dataaccess/view-service`, `eurex/specification/view-model` | AD Trading Architecture (U) |
| Reference Data Cache | RDC | Library that aggregates and distributes reference data across components | `common/dataaccess/rdc`, `eurex/dataaccess/rda-common`, `eurex/dataaccess/rda-outbound-bridge`, `common/dataaccess/rda-inbound-bridge`, `common/dataaccess/rda-outbound-bridge-common` | AD Trading Architecture (U) |
| Logical Data Store | LDS | Persistence layer for recoverable state across components | `eurex/apps/persistence` | AD Trading Core (U) |
| Gateway Plug Interface | gameinterface | Gateway plug-in interface library (C++ `namespace gateway`) defining the abstraction between the Gateway and the Matcher (`GWPlugInterface.hxx`, `MatcherInterface.hxx`, `GatewayPlugCreator.hxx`). Consumed by `eurex/gateway/common` and `eurex/apps/matcher`. **Note:** previously documented here as "MARS — Market Access Risk Shield" exposed via a "GAME (Gateway Algorithmic Market-access Engine)" interface; those expansions are **unverified** — no `eurex/apps/mars`, `eurex/apps/marsgwval`, or `eurex/intmsg/model/mars` component exists in the indexed codebase (releases 140.008.090 / 141.006.050 / 150.002.010), and `gameinterface` is a gateway↔matcher plug interface, not a member-facing risk shield. | `eurex/gateway/gameinterface` | AD Interface Design & Gateways (U) |
| Order Drop Copy Service | ODCS | Provides drop-copy delivery of order and execution data to additional authorized recipients (e.g., clearing members, risk supervisors), supplementary to the primary ETI/FIX channels. Comprises an ODC server and an ODC gateway. | `eurex/apps/odcserver`, `eurex/gateway/odcgw`, `eurex/gateway/odcgwconversion`, `eurex/intmsg/model/odc` | AD Interface Design & Gateways (U) |

---

## Market Data Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| EOBI Publisher | EOBI | Publishes full order-book market data in real-time, order-by-order, via multicast UDP (Enhanced Order Book Interface). Driven by Matcher audit trail output. | `eurex/apps/market-data-obo-incremental`, `eurex/intmsg/model/multicaster` | AD Trading Core (U) |
| Netted Market Data | MDI | Publishes best-bid/ask and limited-depth (netted, price-level-aggregated) market data to participants (Market Data Interface / Extended MDI). | `eurex/apps/market-data-netted`, `eurex/apps/market-data-republisher` | AD Trading Core (U) |
| Market Data Heartbeat | MDH | Sends periodic heartbeat messages on market data multicast channels so participants can detect feed interruptions. | `eurex/apps/market-data-heartbeat` | AD Trading Core (U) |
| Multicaster | — | Low-level multicast packet distribution layer used by EOBI and MDI publishers to distribute market data via UDP multicast. | `eurex/apps/multicaster` | AD Trading Core (U) |

---

## Gateway Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| ETI Gateway | GW / GwLF | Primary participant gateway — ETI session management, order entry, protocol handling, throttling, subscription management. | `eurex/gateway/gateway`, `eurex/gateway/gwconversion`, `eurex/intmsg/model/gateway` | AD Interface Design & Gateways (U) |
| FIX Gateway | GwFIX | FIX 5.0 SP2 participant gateway — translates FIX protocol messages to internal ETI-backed request/response flows. | `eurex/gateway/fixgw`, `eurex/gateway/fix`, `eurex/gateway/fixgwconversion`, `eurex/intmsg/model/fixgw` | AD Interface Design & Gateways (U) |
| ODC Gateway | GwODC | Gateway for the Order Drop Copy service — routes drop-copy data to authorized recipients. | `eurex/gateway/odcgw`, `eurex/gateway/odcgwconversion`, `eurex/intmsg/model/odc` | AD Interface Design & Gateways (U) |
| GatewayGSE | GwGSE | Frankfurt Application GSE gateway (FAGSE) — legacy mainframe-oriented gateway for specialized order flow. Owned by Mainframe Application Development. | `eurex/apps/fagse`, `eurex/gateway/common` | Mainframe Application Development (U) |

---

## Protocol / Interface Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| Enhanced Trading Interface | ETI | Binary protocol for high-performance order entry (participants) | `eurex/gateway/eti`, `eurex/apps/etiasm` | AD Interface Design & Gateways (U) / AD OPM & Cloud Simulation (U) |
| FIX Gateway | FIX | FIX protocol adapter for standard market connectivity | `eurex/gateway/fix`, `eurex/gateway/fixgw`, `eurex/gateway/fixgwconversion`, `eurex/gateway/fixgw-rule_gen`, `eurex/intmsg/model/fixgw` | AD Interface Design & Gateways (U) |
| External Data and Clearing Interface | EDCI | Protocol library and documentation for external clearing data exchange — used for clearing-integration data flows between T7 and Eurex Clearing systems. **Note:** The abbreviation EDCI is also used for the participant-facing "Enhanced Drop Copy Interface" (EDC service) — context determines which is meant. | `eurex/gateway/edci`, `eurex/gateway/edci-docu` | AD Interface Design & Gateways (U) |

---

## Infrastructure / Platform

| Component | Responsibility | Key Repositories |
|-----------|----------------|------------------|
| commondb | Central configuration DB — process topology, partition/market mapping, pool definitions | `eurex/dataaccess/commondb-database`, `eurex/dataaccess/commondb-database-conversion` |
| rdb | Reference data DB — products, instruments, markets, business units | `eurex/dataaccess/rdb-database`, `eurex/apps/refdata-database` |
| viewdb_\<marketplace\> | Per-marketplace ViewDB instance (e.g. `viewdb_eurex`, `viewdb_xetr`) | `eurex/dataaccess/viewdb-database`, `common/dataaccess/viewdb-database-common` |
| tesdb | TES last-IDs and product off-book tracking | `eurex/dataaccess/tradeentryservice` |
| patedb\<PartitionID\> | Per-partition PATE database instance — stores audit trail persistence data and PTRL state | `eurex/apps/pate` |
| exportdb | Export database — persists data for external reporting and file-based exports | `eurex/dataaccess/exportdb-database` |

---

## Supporting / Auxiliary Components

| Component | Abbreviation | Responsibility | Key Repositories | Department |
|-----------|-------------|----------------|------------------|------------|
| Audit Trail Filter | auditfilter | Filters and processes Matcher audit trail messages — downstream consumer of Matcher audit stream, provides selective forwarding and transformation of audit records. | `eurex/apps/auditfilter`, `eurex/apps/test/tools/auditstream` | AD Trading Core (U) |
| ETI ASM | ETI ASM | ETI Application State Manager — manages session state for ETI participants; used by the OPM (Online Performance Monitor) infrastructure. | `eurex/apps/etiasm` | AD OPM & Cloud Simulation (U) |
| Connection Test Gateway | CTestGw | Lightweight gateway used in integration tests to simulate participant connectivity without a full T7 session. | `eurex/apps/connection-test-gateway` | AD Trading Architecture (U) |
| Market Data Republisher | — | Republishes netted market data for additional downstream consumers or failover scenarios. | `eurex/apps/market-data-republisher` | AD Trading Core (U) |
| News Service | News | Delivers exchange news messages to connected participants via the T7 session. | `eurex/apps/newsservice` | AD Trading Core (U) |

---

## Key Structural Concepts

| Concept | Description |
|---------|-------------|
| Partition | A logical grouping of instruments processed by one Matcher instance. Each partition runs on dedicated server capacity. |
| Market | A trading venue identified by MarketID and MIC (e.g. `XEUR` = Eurex derivatives, `XETR` = Xetra cash) |
| Marketplace | The top deployment layer — a logical grouping of markets that share the same matching-engine instance and operational topology. Many per-instance artifacts are scoped per marketplace (e.g. `viewdb_<marketplace>` such as `viewdb_EUREX`, `viewdb_XETCASH`). One marketplace contains one or more markets; each market belongs to exactly one marketplace. |
| Pool | A set of partitions assigned to a physical matching server |
| Baseline | A named T7 software release (e.g. 14.0, 14.1); each baseline has its own indexed codebase instance |
| Instrument State | Lifecycle state of a tradeable instrument. States include: `Continuous` (continuous matching active), `Pre-Call` (pre-auction), `Auction` (call phase — collecting orders, no matching), `Freeze` (auction frozen pending operator action), `Trade-at-Close` (matching at closing auction price only), `Restricted` (order maintenance restricted), `Suspended` (instrument halted), `Knock-Out` (knocked out — structured products), `Expired` (past expiry, inactive). |
| Market State / Product State | Session state of a market or product group. States include: `Pre-Trading` (system ready, no trading), `Opening Auction` / `Intraday Auction` / `Closing Auction` (auction call active), `Trading` / `Continuous` (on-book continuous matching active), `Post-Trading` (trading ended, settlement in progress), `End-of-Day` (EOD processing complete), `Halt` (product-wide trading halted), `Closed`. |
| Trading Model | The configured market model for a product or instrument type. Examples: *Continuous Trading with Auctions* (standard derivatives/cash model), *Continuous Auction with Market Maker* (WBAG structured products), *Continuous Auction with Specialist* (Frankfurt floor-based products). |
| Allocation Method | The rule used to distribute quantity among competing orders at the same price level. Options: *Price-Time Priority* (FIFO — first-arrived order fills first), *Pro-Rata* (fill proportional to order size), *Time-Pro-Rata* (minimum guaranteed fill to oldest, remainder pro-rata). |

---

## PATE Architecture History

| Release | Event |
|---------|-------|
| Pre-R10 | Two separate components: **PoPE** (Post Processing Engine) — audit trail and trade record creation; **TRAM** (Trade Manager) — downstream notification distribution |
| R10.0 | PoPE + TRAM merged into **PaTe** (Post-Processing And Trade Engine); moved to Unio/HotPipe framework; `RETRANSMISSION_RESPONSE` target introduced |
| R11.0 | MySQL/StreamDB replaced by stream-based file persistence (memory-mapped files); Persistency Plugin + Retransmission Plugin separated out |
| R11.1 | `BCSettlementPrices` broadcast to Market Data Hub (MDH) added |
| R12.0 | `BCSettlementInputData` broadcast to Control GUI; TES Manager adopts PaTe's persistency layer |
| R13.x | Variance Futures deal-update support; dual-notation broadcasts |
| R14.1 | Officially renamed **Post Processing and Audit Trail Engine**; HAT retransmission service; Retransmission Plugin hardened for high availability |

PATE's two output dimensions:
- **Public path**: OFI → TFH → C7 (clearing) — legally binding trade records
- **Private path**: GW → ETI/FIX → participants — trade confirmations and execution reports

Source: Confluence "T7 PaTe — Knowledge Base" (page 782270474), DTS141405, DFS10015.

---

## Search Guidance by Topic

| If the query is about... | Start searching in... |
|--------------------------|----------------------|
| Order matching, price calculation, priority | Matcher — search `matching`, `order_book`, `price_determination` |
| Session management, login, throttle | Gateway — search `session`, `throttle`, `logon`, `ETI` |
| TES trade lifecycle | OFI / TES — search `tes_trade`, `approval`, `negotiation` |
| Pre-trade risk limits (PTRL), kill switch, position limits | PATE (`patedb`) — search `pretraderisklimits`, `risk_limit`, `kill_switch`, `position`. Note: PATE stores PTRL state in `patedb`; the enforcement logic is in the Gateway and Matcher. |
| Post-trade processing, audit trail, deal creation, trade records | PATE — search `audit_trail`, `deal`, `trade_record`, `post_processing` |
| Instrument/product data | RDD — search `reference_data`, `instrument_descriptor` |
| Materialized reference/config views, instrument & product descriptors, statistics, GUI data | ViewDB — search `viewdb`, `RdaInstrumentDerivatives`, `Rda`, `GUI`, `post_process`, `statistics` (built on `rdb` + `commondb`) |
| Margin, clearing | Prisma / RDC — search `margin`, `clearing`, `prisma` |
| Configuration, topology | commondb — search `partition`, `pool`, `process_config` |
| Market data multicast (real-time order book) | EOBI Publisher (`market-data-obo-incremental`) — search `eobi`, `order_book_update`, `multicast` |
| Netted market data (price levels) | MDI (`market-data-netted`) — search `mdi`, `price_level`, `depth`, `netted` |
| Drop copy (order/trade copies to 3rd parties) | ODCS — search `drop_copy`, `odcserver`, `odc_gateway` |
| Enhanced drop copy (EDC — lean orders, all order events for risk monitoring) | ODCS / EDC — search `edci`, `extended_order_information`, `edc_session` |
| Gateway↔Matcher plug interface | gameinterface — search `GWPlugInterface`, `MatcherInterface`, `GatewayPlugCreator` (note: no `mars`/`risk_shield` component exists in the indexed codebase) |
| Audit trail filtering | auditfilter — search `audit_filter`, `audit_stream` |
| FIX protocol processing | FIX Gateway — search `fixgw`, `fix_conversion`, `FIXSession` |
| Clearing data exchange (internal, to ECAG) | EDCI — search `edci`, `clearing_interface` |
| SMP / self-match prevention | Matcher / Gateway — search `smp`, `self_match`, `MatchInstCrossID`, `SelfMatchPreventionInstruction` |
| MMP / market maker protection | Matcher — search `mmp`, `market_maker_protection`, `QuoteActivation`, `quote_deactivation` |
