---
name: t7-spec
description: "T7 Trading System specification and domain knowledge. Use when: reading, writing, or referencing T7 functional specifications, interface documents, or FIX protocol specs; understanding order lifecycle states; identifying instrument types; naming reference documents."
systems: [t7]
---

# T7 Spec — Functional Specification & Domain Knowledge

Use this skill when working with T7 functional specifications, interface definitions, protocol documentation, or any domain-level design questions about the T7 Trading System.

---

## T7 FSD (Functional Specification Document) Structure

Every T7 FSD follows this standard section layout:

| Section | Title | Content |
|---------|-------|---------|
| 1 | Overview | Purpose, scope, audience |
| 2 | System Context | Actors, external systems, deployment overview |
| 3 | Functional Requirements | Numbered requirements (`FR-{component}-{NNN}`) |
| 4 | Interface Specifications | API contracts, message schemas, FIX tag definitions |
| 5 | Data Model | Entity descriptions, key fields, relationships |
| 6 | Business Rules | Validation logic, risk checks, matching rules |
| 7 | Order Lifecycle | State machine diagram + transition table |
| 8 | Error Handling | Error codes, rejection reasons, recovery flows |
| 9 | Non-Functional Requirements | Latency SLAs, throughput targets, availability |
| 10 | Open Issues | Unresolved questions, decisions pending |

### Requirement ID Format
- Functional: `FR-{COMPONENT}-{NNN}` (e.g. `FR-CORE-042`, `FR-GW-017`)
- Non-functional: `NFR-{COMPONENT}-{NNN}` (e.g. `NFR-CORE-001` for latency target)
- Interface: `IF-{COMPONENT}-{NNN}` (e.g. `IF-GW-FIX-003` for a FIX message definition)

---

## Reference Document Naming Convention

All T7 reference documents follow this pattern:

```
T7-{component}-{type}-v{version}.pdf
```

Examples:
- `T7-Core-FSD-v2.1.pdf` — Core Engine Functional Specification, version 2.1
- `T7-Gateway-FIX-Interface-v1.4.pdf` — Gateway FIX interface document
- `T7-Admin-UI-UX-Guide-v1.0.pdf` — Admin UI UX specification
- `T7-Database-Schema-v3.0.pdf` — Database schema reference
- `T7-System-Architecture-v2.3.pdf` — Full system architecture overview

Components: `Core`, `Gateway`, `Admin`, `Database`, `System`
Types: `FSD`, `FIX-Interface`, `ITCH-Interface`, `OUCH-Interface`, `Schema`, `Architecture`, `UX-Guide`, `Release-Notes`

---

## FIX Protocol Basics for T7

T7 uses the **FIX 5.0 SP2** protocol for order entry and execution reporting between participants and the Gateway.

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
| 39 | `OrdStatus` | `0`=New, `1`=PartiallyFilled, `2`=Filled, `4`=Cancelled, `8`=Rejected |
| 40 | `OrdType` | `1`=Market, `2`=Limit, `3`=Stop, `4`=StopLimit |
| 44 | `Price` | Limit price (required for Limit and StopLimit orders) |
| 49 | `SenderCompID` | Identifies the sending participant |
| 54 | `Side` | `1`=Buy, `2`=Sell |
| 55 | `Symbol` | Instrument identifier (ISIN or internal symbol) |
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

---

## ITCH / OUCH Protocol Basics

### ITCH (Market Data — inbound to participants)
Binary protocol for high-speed market data delivery from T7 to participants.

| Message Type | Description |
|---|---|
| `A` (AddOrder) | New order added to the book |
| `E` (OrderExecuted) | Order fully or partially executed |
| `D` (OrderDeleted) | Order removed from the book (cancel/expire) |
| `U` (OrderReplaced) | Order amended (price or quantity changed) |
| `P` (TradeMessage) | Executed trade record |
| `S` (SystemEvent) | Session state notifications (start/end of trading) |

### OUCH (Order Entry — outbound from participants)
Binary protocol for low-latency order submission from participants to T7.

| Message Type | Description |
|---|---|
| `O` (EnterOrder) | Submit a new order |
| `U` (ReplaceOrder) | Amend price or quantity of an existing order |
| `X` (CancelOrder) | Cancel an existing order |
| `A` (OrderAccepted) | Exchange confirms order accepted |
| `R` (OrderRejected) | Exchange rejects order with reason code |
| `E` (OrderExecuted) | Execution confirmation for OUCH order |
| `C` (OrderCanceled) | Confirmation of cancellation |
