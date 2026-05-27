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

EOBI feeds are organised by **partition** (matching engine partition). Participants subscribe per product.

---

## ETI — Enhanced Transaction Interface

ETI is T7's primary **order entry** interface. It is a binary, session-based protocol offering the lowest latency. All FIX LF sessions are internally backed by ETI sessions.

### Key ETI Request/Response Message Families

| Family | Example Messages |
|--------|------------------|
| Order management | `NewOrderRequest`, `ModifyOrderRequest`, `DeleteOrderRequest` |
| Quote management | `MassQuoteRequest`, `DeleteAllQuoteRequest` |
| TES (T7 Entry Service) | `TESNewTradeRequest`, `TESApproveTrade` |
| SRQS (Selective RfQ) | `SRQSOpenNegotiationRequest`, `SRQSDealNotification` |
| Session / risk | `UserLoginRequest`, `Subscribe`, `RetransmitRequest` |

Broadcast (push) notifications are returned on a separate **broadcast connection** per session.