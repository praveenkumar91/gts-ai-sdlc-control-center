# T7 Interfaces Reference

---

## T7 Interface Landscape

T7 exposes several distinct interfaces. The primary order entry interface is **ETI**, not FIX.

| Interface | Full Name | Purpose |
|-----------|-----------|---------|
| **ETI** | Enhanced Transaction Interface | High-performance binary order entry; lowest latency |
| **FIX LF** | FIX Low Frequency Gateway | FIX 5.0 SP2 order entry for participants using FIX |
| **EOBI** | Enhanced Order Book Interface | Full order-book public market data (real-time, binary, multicast) |
| **MDI / EMDI** | Market Data Interface / Extended MDI | Netted and extended market data |
| **RDI / RDF** | Reference Data Interface / Feed | Instrument reference data |
| **T7 GUI / Trader GUI** | Graphical User Interface | Browser-based manual trading and control |

---

## FIX LF (Low Frequency) Interface

T7's FIX interface is called **FIX LF** and is based on **FIX 5.0 SP2**. It is a secondary interface for participants who cannot use ETI. The FIX LF session is backed by one or more ETI sessions on the Gateway.

### Key Message Types

| MsgType | Name | Direction | Description |
|---------|------|-----------|-------------|
| `D` | NewOrderSingle | Client → T7 | Submit a new order |
| `F` | OrderCancelRequest | Client → T7 | Cancel an existing order |
| `G` | OrderCancelReplaceRequest | Client → T7 | Amend price or quantity of an existing order |
| `8` | ExecutionReport | T7 → Client | Confirms order state change (new, fill, cancel, reject) |
| `9` | OrderCancelReject | T7 → Client | Rejection of a cancel or amend request |
| `V` | MarketDataRequest | Client → T7 | Subscribe to market data |
| `W` | MarketDataSnapshotFullRefresh | T7 → Client | Full order book snapshot |
| `X` | MarketDataIncrementalRefresh | T7 → Client | Incremental order book update |

### Key FIX Tags

| Tag | Name | Values / Notes |
|-----|------|----------------|
| 11 | `ClOrdID` | Unique client order identifier (string, max 20 chars) |
| 37 | `OrderID` | Exchange-assigned order identifier |
| 38 | `OrderQty` | Requested order quantity |
| 39 | `OrdStatus` | `0`=New, `1`=PartiallyFilled, `2`=Filled, `4`=Cancelled, `8`=Rejected, `D`=Cancelled(Replaced), `H`=Restated, `E`=PendingReplace |
| 40 | `OrdType` | `1`=Market, `2`=Limit, `3`=Stop, `4`=StopLimit |
| 44 | `Price` | Limit price (required for Limit and StopLimit orders) |
| 49 | `SenderCompID` | Identifies the sending participant |
| 54 | `Side` | `1`=Buy, `2`=Sell |
| 48 | `SecurityID` | Instrument identifier (T7 uses SecurityID + SecurityIDSource, not Symbol) |
| 22 | `SecurityIDSource` | Identifies the security ID type (e.g. `M`=Marketplace-assigned) |
| 58 | `Text` | Free-text reject reason (in `ExecutionReport` and `OrderCancelReject`) |
| 59 | `TimeInForce` | `0`=Day, `1`=GTC, `3`=IOC, `4`=FOK |
| 150 | `ExecType` | `0`=New, `1`=PartialFill, `2`=Fill, `4`=Cancelled, `8`=Rejected |
| 151 | `LeavesQty` | Remaining open quantity |
| 14 | `CumQty` | Total filled quantity so far |

### FIX Session Lifecycle
1. `Logon (A)` — establish session; exchange sequence numbers
2. Exchange messages — orders, executions, market data
3. `Heartbeat (0)` — keep-alive every `HeartBtInt` seconds
4. `TestRequest (1)` / `Heartbeat (0)` — liveness check
5. `Logout (5)` — graceful session termination

---

## Order Lifecycle States

```
                    ┌─────────────────────────────────┐
                    │                                 │
         Submit     ▼          Partial Fill           │
Client ──────────► New ──────────────────────► PartiallyFilled
                    │                                 │
          Rejected  │  Cancelled                      │ Filled / Cancelled
                    ▼       ▼                         ▼
                 Rejected  Cancelled ◄─────────── Filled (terminal)
               (terminal) (terminal)
```

### State Transition Table

| From State | Event | To State | ExecType (tag 150) | OrdStatus (tag 39) |
|------------|-------|----------|--------------------|--------------------|
| — | `NewOrderSingle` accepted | New | `0` (New) | `0` (New) |
| — | `NewOrderSingle` rejected | Rejected | `8` (Rejected) | `8` (Rejected) |
| New | Partial fill | PartiallyFilled | `1` (PartialFill) | `1` (PartiallyFilled) |
| New | Full fill | Filled | `2` (Fill) | `2` (Filled) |
| New | Cancel accepted | Cancelled | `4` (Cancelled) | `4` (Cancelled) |
| PartiallyFilled | Additional fill | PartiallyFilled | `1` (PartialFill) | `1` (PartiallyFilled) |
| PartiallyFilled | Remaining qty filled | Filled | `2` (Fill) | `2` (Filled) |
| PartiallyFilled | Cancel accepted | Cancelled | `4` (Cancelled) | `4` (Cancelled) |

Terminal states: **Filled**, **Cancelled**, **Rejected** — no further transitions possible.

> **Note:** This table covers the common path only. T7 also uses `Suspended`, `PendingNew`, `PendingCancel`, `PendingReplace`, and `Restated` states. Consult the ETI or FIX LF reference manual for the full state machine.

---

## T7 Instrument Types

### Equity (Cash Market)
- Shares, ETFs, certificates traded on cash market segment
- Settlement: T+2 (standard European cash settlement)
- Tick size: defined per instrument in reference data
- No margin requirement — full settlement value required
- Matching: price-time priority

### Futures
- Standardised contracts on equity indices (e.g. DAX futures), commodities
- Settlement: cash or physical delivery, defined per product
- Margin: initial and variation margin calculated daily
- Expiry: quarterly (March, June, September, December) or monthly series
- Matching: price-time priority within same contract series

### Options
- Equity options (single-stock) and index options
- Exercise styles: **European** (index options — exercise at expiry only) or **American** (equity options — exercise any time)
- Premium: upfront, paid at trade
- Series identified by: underlying, expiry date, strike price, call/put flag
- Matching: price-time priority

> **Note:** T7 also handles Bonds, Warrants, Certificates, ETPs, and Combination/Spread products. The above covers the most common categories.

---

## EOBI — Enhanced Order Book Interface

EOBI is T7's primary **public market data** interface. It delivers the full visible order book in real-time, order-by-order, via multicast UDP. It is a binary protocol.

### Key Characteristics (Source: Eurex EOBI Member Manual v1.0.2; MTD141032 EMDI Manual R14.1)

- **Full order depth** — no depth restriction; all visible orders and quotes are published without limit.
- **Fixed-length binary messages** using FIX-standard encoding to minimise integration effort.
- **Incremental messages** (triggered by each state change) plus **Snapshot messages** (periodic full-book rebuild).
- Snapshot message publishing order:
  1. Side — bid side published first, offer side second.
  2. Price — best price first.
  3. Time — highest time-priority order first within same price.
- Separate multicast address/port combinations from EMDI and MDI feeds.
- Feeds are organised by **partition** (matching engine partition). Participants subscribe per product.
- Driven by the Matcher audit trail via the EOBI Publisher component (`eurex/apps/market-data-obo-incremental`).

### Key EOBI Message Types

| Message | Description |
|---------|-------------|
| `OrderAdd` | New order/quote side added to the book |
| `OrderModify` | Order price or quantity amended |
| `OrderDelete` | Order removed from the book (cancel/expire) |
| `OrderMassDelete` | Bulk deletion of orders (e.g. on session disconnect) |
| `FullOrderExecution` | Order fully executed |
| `PartialOrderExecution` | Order partially executed |
| `TradeReversal` | Previously reported trade reversed |
| `ProductSummary` | Snapshot of product-level state |
| `InstrumentSummary` | Snapshot of instrument-level state |
| `PacketHeader` | Multicast packet header (sequence number, timestamp) |

---

## ETI — Enhanced Transaction Interface

ETI is T7's primary **order entry** interface. It is a binary, session-based protocol offering the lowest latency. All FIX LF sessions are internally backed by ETI sessions.

### Key ETI Request/Response Message Families

| Family | Example Messages |
|--------|------------------|
| Order management | `NewOrderRequest`, `ModifyOrderRequest`, `DeleteOrderRequest` |
| Mass operations | `MassOrderRequest`, `DeleteAllOrderRequest` |
| Quote management | `MassQuoteRequest`, `DeleteAllQuoteRequest`, `QuoteActivationRequest` |
| TES (T7 Entry Service) | `TESNewTradeRequest`, `TESApproveTrade` |
| SRQS (Selective RfQ) | `SRQSOpenNegotiationRequest`, `SRQSDealNotification` |
| Session / risk | `UserLoginRequest`, `Subscribe`, `RetransmitRequest` |
| EDC (Enhanced Drop Copy) | `ExtendedOrderInformation` (received; via separate EDCI connection) |

Broadcast (push) notifications are returned on a separate **broadcast connection** per session.

### ETI Session Types

| Session Type | Purpose |
|--------------|---------|
| High-Frequency (HF) | Order entry — lowest latency, typically for automated trading |
| Low-Frequency (LF) | Order entry — standard latency for manual or semi-automated trading |
| Back-Office (BACKOFFICE) | Receiving drop copies of order/execution data for the BU |
| GUI | Used by T7 Trader GUI; lower throughput than HF/LF |

> Source: MTD141011 ETI Reference Derivatives R14.1; MTD141015 FIX LF Manual R14.1.

---

## EDCI — External Data and Clearing Interface

EDCI is T7's clearing integration protocol library used for exchanging clearing-related data flows between T7 and Eurex Clearing AG (ECAG). It is an internal interface — not participant-facing.

- Repository: `eurex/gateway/edci`, `eurex/gateway/edci-docu`
- Owner: AD Interface Design & Gateways (U)
- Used for: clearing member data, position data, and settlement-related messages flowing between T7 trading components and the Eurex Clearing infrastructure.

> **Abbreviation note:** The abbreviation `EDCI` is shared between two distinct concepts:
> 1. **External Data and Clearing Interface** — internal clearing integration library (described above).
> 2. **Enhanced Drop Copy Interface** — the participant-facing order drop-copy connection (described in the EDC section below).
> Context determines which is intended.

---

## EDC — Enhanced Drop Copy Interface

> Source: DFS141420 Enhanced Drop Copy Enhancements Part 1 R14.1; DFS130315 Enhanced Drop Copy Authorization Concept.

The **Enhanced Drop Copy (EDC)** service (also referred to as EDCI — Enhanced Drop Copy Interface) is a participant-facing interface for comprehensive order monitoring and pre-trade risk management. It is conceptually separate from the ODCS (Order Drop Copy Service) and the internal EDCI clearing library.

### Purpose

- Designed for participants seeking **enhanced pre-trade risk monitoring** or a **complete overview of their order inventory**, including lean orders (which are not included in standard ETI/FIX confirmations).
- Accessible by **Trading Participants** for their own Business Unit, and by **Clearing Members** who provide clearing services to those Trading Participants (CM requires authorization from the TP).

### Connection and Data Flow

1. Participant application opens a TCP/IP connection to T7.
2. The drop-copy stream starts with a `TradingSessionEvent` message (_Start of Order Book Synchronization_) per partition.
3. Active orders are restated via `ExtendedOrderInformation` messages.
4. `TradingSessionEvent` (_End of Order Book Synchronization_) marks the end of the initial restatement.
5. Ongoing updates are delivered as additional `ExtendedOrderInformation`, `TradingSessionEvent`, and `Order(Mass)CancellationNotification` messages.
6. `TradingSessionEvent` (_End of Service_) marks end of the drop-copy stream for the business day.

> **Note:** Quotes, Cross Requests, RfQs, and CLIP Requests are currently out of scope for EDC.

### Configuration

EDC sessions are ordered and configured via the **T7 Clearer GUI** or **T7 Admin GUI**. The Clearing Member accesses the TP's data via the _Enhanced Drop Copy Access Requests_ view after the TP grants authorization.

### R14.1 Enhancements (planned at time of writing)

- EDCI will send volatility interruption events in correct logical sequence (separate NEW + CANCEL instead of conflated CANCEL only).
- New EDC notifications for CLIP Requests and Cross Requests covering every step.
- New RfQ Notification for request-for-quote workflows.
- SMP-related fields added: `MatchInstCrossID`, `SelfMatchPreventionInstruction`, `CrossMatchInstruction`.
- Retransmission support: participants can request retransmission from a specific sequence number or from start of business day.

---

## Instrument States Reference

T7 controls order and quote activity per instrument through a set of well-defined instrument states. The following table summarises the key states:

| Instrument State | Matching Active? | Order Maintenance? | Description |
|------------------|-----------------|-------------------|-------------|
| `Continuous` | Yes | Yes | Continuous price-time matching; orders matched immediately on entry. |
| `Pre-Call` | Limited | Yes | Pre-auction phase; limited matching in some trading models before the Auction-Call. |
| `Opening Auction` | No (until uncrossing) | Yes | Opening auction call — orders collect before uncrossing at open. |
| `Intraday Auction` | No (until uncrossing) | Yes | Intraday auction triggered by VI or scheduled event. |
| `Closing Auction` | No (until uncrossing) | Yes | Closing auction call — determines official closing price. |
| `Volatility Auction` | No (until uncrossing) | Yes | Volatility interruption — triggered when potential execution falls outside the price collar. |
| `Freeze` | No | Restricted | Auction frozen by operator; awaiting manual intervention before uncrossing. |
| `Trade-at-Close` | At closing price only | Yes | Post-closing auction phase — matching occurs at the fixed closing auction price only; no price discovery. |
| `Restricted` | No | Restricted | Order maintenance severely restricted; no matching. |
| `Suspended` | No | No | Instrument halted; no trading activity permitted. |
| `Knock-Out` | No | No | Structured product knocked out; no further trading. |
| `Expired` | No | No | Instrument past its expiry date; inactive. |

Source: MFG141002 T7 Functional Reference v14.1, §3 Instrument States.

---

## Trading Models

T7 supports several trading models, each defining the sequence of instrument states during the business day:

| Trading Model | Typical Exchanges | Description |
|---------------|------------------|-------------|
| *Continuous Trading with Auctions* | Eurex, Xetra, EEX | Standard model — opening auction → continuous trading → (optional intraday auctions) → closing auction. Most derivatives and cash products. |
| *Continuous Auction with Market Maker* | WBAG (Vienna, Budapest, etc.) | Market maker provides quotes; order book uncrosses immediately on matching quote entry (Auction-Call phase). |
| *Continuous Auction with Specialist* | Deutsche Börse Frankfurt | Specialist controls trading phases manually; Freeze state allows operator-controlled uncrossing; Pre-Call and Freeze alternate. |

---

## Volatility Interruption (VI)

A **Volatility Interruption** is triggered automatically when the potential execution price of an order would fall outside the configured price corridor:

- **Static collar** — a fixed price band around the reference price (e.g. settlement price or previous close).
- **Dynamic collar** — an adaptive band updated after each trade to track recent market prices.

On VI trigger:
1. Continuous trading is suspended immediately.
2. Instrument transitions to `Volatility Auction` call state.
3. An auction call phase begins (configurable duration).
4. The instrument either uncrosses or transitions to `Freeze` if the order book is still outside the collar.

Source: MFG141002 T7 Functional Reference v14.1, §7.5 Volatility Interruptions.

---

## Quote Lifecycle and Market Maker Protection (MMP)

> Source: MFG141002 T7 Functional Reference v14.1, §5.5–5.6.

### Quote Activation / Deactivation

A session's quotes can be **deactivated** per product. When deactivated:
- Quotes do **not** participate in matching and are not used for market price calculations.
- Quotes can still be maintained (modified, deleted) while inactive.
- New quotes entered while the session is inactive for a product remain inactive.
- Deactivation status is **persistent**: it survives session disconnect and Matcher restart. At start of day, all sessions are reset to active.

On **reactivation**, for each quote in sequence:
1. Priority timestamp is updated (new time priority).
2. Extended Price Range Validation applied — quote deleted if outside allowed range.
3. If instrument state is `Continuous` and the quote is executable, it is matched as an incoming quote.

### Market Maker Protection (MMP)

MMP automatically deactivates a market maker's quotes when configurable breach thresholds are hit within a defined time window. Thresholds can be based on:
- **Number of executions** within the window.
- **Cumulative executed volume** within the window.

The scope of MMP parameters (deactivation thresholds) must match the scope of the quote activation — both apply per **product**. MMP triggers an automatic deactivation, which then follows the same reactivation flow as a manual deactivation.

> MMP protects liquidity providers from excessive automated execution against their quotes in fast market conditions.

### Book-Or-Cancel (BOC) Quotes

BOC quotes are posted to the order book **without matching on entry**. If the BOC quote would be executable on entry, it is **rejected** entirely. After posting, a BOC quote can be matched passively (e.g., if a market order arrives). If one side of a two-sided BOC quote is rejected, the other side is also rejected.

---

## Self-Match Prevention (SMP)

> Source: DFS3008 Self-Match Prevention v1.4; DFS140420 SMP Enhancements R14.0.

SMP prevents an incoming order from matching against a resting order or quote from the **same Business Unit** in the same instrument. Two variants:

| SMP Type | Scope | Mechanism |
|----------|-------|-----------|
| **Type A** | Cross ID group | Orders with matching `Cross ID` (MatchInstCrossID) in the same BU will not match each other. Requires Cross ID to be explicitly set on both orders. |
| **Type B** | Session-based | Orders from the same ETI/FIX session will not match each other. Applies without requiring a Cross ID. |

A **default SMP Instruction** can be configured per product (from RDA): applied when the incoming order does not carry an explicit SMP instruction but has a `MatchInstCrossID` set.

> SMP is optional and configured per market/product. It is not available on all T7 venues.

---