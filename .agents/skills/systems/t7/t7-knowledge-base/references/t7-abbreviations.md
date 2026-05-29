# T7 Abbreviations & Terminology Reference

> Comprehensive glossary of T7 trading system terms, abbreviations, and definitions.
> Sources: MFG141002 T7 Functional Reference v14.1 (March 2026), T7 spec corpus (DFS/SRQ/MTD documents), T7 Knowledge Base reference files (t7-interfaces.md, t7-modules.md, t7-applications.md, t7-terminology.md).
> Last updated: 2026-05-28

---

## Table of Contents
- [T7 Abbreviations \& Terminology Reference](#t7-abbreviations--terminology-reference)
  - [Table of Contents](#table-of-contents)
  - [System Components \& Architecture](#system-components--architecture)
  - [Market Participants \& Roles](#market-participants--roles)
  - [Instruments \& Products](#instruments--products)
  - [Order Types \& Attributes](#order-types--attributes)
  - [Trading Concepts \& Market Operations](#trading-concepts--market-operations)
  - [Protocols \& Interfaces](#protocols--interfaces)
  - [Risk \& Clearing](#risk--clearing)
  - [Operational Terms](#operational-terms)
  - [TES \& Off-Book Trading](#tes--off-book-trading)
  - [Eurex EnLight / SRQS](#eurex-enlight--srqs)
  - [Document Types \& Regulatory Abbreviations](#document-types--regulatory-abbreviations)
  - [Codebase Search Term Mappings](#codebase-search-term-mappings)
    - [Release naming](#release-naming)
    - [Order Types](#order-types)
    - [Matching](#matching)
    - [Instruments](#instruments)
    - [Risk](#risk)
    - [Protocols](#protocols)
    - [TES](#tes)
    - [Configuration](#configuration)

---

## System Components & Architecture

| Abbreviation | Full Name | Definition |
|---|---|---|
| Baseline | — | A named T7 software release (e.g., 14.0, 14.1); each has its own indexed codebase instance. |
| CoMa | Contract Manager | Manages creation and configuration of complex instrument contracts. Repos: `eurex/apps/contractmanager`. |
| commondb | Common Database | Central configuration DB storing process topology, partition/market mapping, and pool definitions. |
| GMC | Generic Memory Cluster | The underlying in-memory data distribution framework used by Live Results (LR). |
| GW / Gateway | Gateway | Entry point for participant order flow — handles session management, ETI/FIX protocol handling, and throttling. Repos: `eurex/gateway/gateway`. |
| LDS | Liquidity Discovery Service | A negotiation service for selective request-for-quote workflows; predecessor/related to SRQS. Repos: `eurex/apps/liquidity-discovery-service`. |
| LR | Live Results | In-memory distributed cluster (GMC-based) providing real-time state replication across components. |
| Market | — | A trading venue identified by a MarketID and MIC (e.g., `XEUR` = Eurex derivatives, `XETR` = Xetra cash). |
| Marketplace | — | A logical grouping of markets sharing the same matching engine instance. |
| MON | System Monitor | Monitors the state of T7 components. Repos: `common/controller-monitor/monitor`. |
| ME / Matcher | Matching Engine | Central matching engine — manages the order book, executes matching algorithms, determines prices and order priority. Repos: `eurex/apps/matcher`. |
| ODC / ODCS | Order Drop Copy Service | Service that provides drop-copy of order and execution data to additional recipients. Repos: `eurex/apps/odcserver`. |
| OFI | Outbound Feed Interface / Order and Floor Interface | Handles floor broker and TES order entry and management; routes outbound feeds. Repos: `eurex/gateway/outboundfi`, `eurex/gateway/oficonversion`. |
| PATE / PaTe | Post-Processor Trading Engine / Pre-Trade Risk Server | Handles pre-trade risk checks — risk limits, kill switch, position tracking per business unit. Repos: `eurex/apps/pate`. |
| patedb | PATE Database | Per-partition PATE database instance for pre-trade risk state. |
| Partition | — | A logical grouping of processes which share the same functional responsibilities. Each partition runs on dedicated server capacity. |
| PerfMon | Performance Monitor | System performance metrics collection and alerting. Repos: `perfmon/core`, `common/perfmon`. |
| Pool | — | A set of partitions assigned to a physical matching server. |
| RDC | Reference Data Cache | Aggregates and distributes reference data across components. Repos: `common/dataaccess/rdc`. |
| rdb | Reference Database | Reference data DB for products, instruments, markets, and business units. |
| RDD | Reference Data Distributor | Distributes instrument and product reference data to internal components. Repos: `eurex/apps/reference-data-distributor`. |
| RDS | Reference Data System | The system managing instrument and product reference data. Repos: `eurex/apps/refdata`. |
| SCS | System Controller | Central controller managing T7 process lifecycle and topology. Repos: `common/controller-monitor/bos`. |
| SEM | Session Manager | Manages session state for trading participants. Repos: `eurex/common/controller-monitor/session`. |
| T7 | T7 Trading System | The cash and derivatives trading platform developed by Deutsche Börse Group, used by Eurex, EEX, Nodal Exchange, Xetra, and partner exchanges. |
| TES | Trade Entry Service | Off-book trade negotiation, approval, and settlement initiation. Supports bilateral and multilateral off-book trades. Repos: `eurex/apps/trade-entry-service`. |
| tesdb | TES Database | Per-product TES last-IDs and off-book tracking. |
| TFH | Trade Feed Handler | Distributes trade confirmations and execution reports to downstream systems. Repos: `eurex/apps/trade-feed-handler`. |
| ViewDB | ViewDB | Read-only market data views — order book snapshots, trade reports, instrument states. Repos: `eurex/dataaccess/viewdb-database`. |

---

## Market Participants & Roles

| Abbreviation | Full Name | Definition |
|---|---|---|
| Account A | Agency Account | Order account type for orders entered on behalf of clients (agency business). |
| Account M | Market Maker Account | Order account type for liquidity provision activities. |
| Account P | Proprietary Account | Order account type for orders entered for the participant's own account (prop trading). |
| BU | Business Unit | An organizational subunit within a participant that groups users and sessions for trading and risk purposes. |
| CM | Clearing Member | A participant with a specific Clearing Business Unit who can clear trades. Responsible for settlement obligations. |
| DC | Direct Client | Current term replacing NCM (Non-Clearing Member). A participant who trades and clears through a Clearing Member rather than directly. |
| DMA | Direct Market Access | A mechanism allowing buy-side clients to enter orders directly to the exchange through a broker's infrastructure. |
| DS | Designated Sponsor | A participant on cash markets obligated to provide liquidity for specific instruments by maintaining quotes. |
| GCM | General Clearing Member | A clearing member authorized to clear for other participants (NCMs/DCs) in addition to itself. |
| Head Trader | — | A user with elevated permissions who can modify/delete orders belonging to other traders in the same trader group. |
| LP | Liquidity Provider | General term for a participant providing liquidity; includes Designated Sponsors, Market Makers, and Regulated Market Makers. |
| MM | Market Maker | A participant providing liquidity by continuously quoting bid and ask prices (account type M). |
| NCM | Non-Clearing Member | Deprecated term. Now called DC market participant (Direct Client). A participant without direct clearing rights who clears through a GCM. |
| Participant | — | A legal entity admitted to trade on a T7 exchange. Synonymous with Member. |
| PTRL | Pre-Trade Risk Limit | A configurable limit on order/quote activity per BU/user, enforced pre-trade by PATE. Can be expressed as quantity or notional value. |
| RLP | Retail Liquidity Provider | A participant providing liquidity specifically for the Xetra Retail Execution (XRE) service with dedicated quote/order types. |
| RMM | Regulated Market Maker | A participant on ETF/ETP markets providing liquidity as required by regulation. |
| SA / SpA | Sponsored Access | A mechanism allowing non-participant entities to access the exchange order book directly via a sponsoring member. |
| Session | — | A technical connection to T7 via ETI or FIX. Each session belongs to a Business Unit. High-frequency, low-frequency, and GUI sessions exist. |
| Supervisor | — | A user within a Business Unit with permissions to modify/delete orders belonging to other users in the same BU. |
| Trader Group | — | A logical grouping of traders within a Business Unit used for ownership and permission controls. |
| User | — | An individual or automated system within a Business Unit authorized to trade. Users are identified by User ID. |

---

## Instruments & Products

| Abbreviation | Full Name | Definition |
|---|---|---|
| American-style option | — | An option that can be exercised at any time up to and including the expiry date. |
| BTRF | Basket Total Return Futures | A TRF based on a basket of equities, entered via the TES basket trading service. |
| Bundle | — | A complex instrument of 8 consecutive quarterly futures (2 packs). Used in interest rate futures. |
| Call Option | — | An option granting the right to buy the underlying at the strike price. |
| CCSPD | Custom Commodity Spread | A user-defined custom spread of commodity strips. |
| CCSTR | Custom Commodity Strip | A user-defined custom strip of commodity futures. |
| Complex Instrument | — | A multi-leg instrument created from two or more simple instruments. Includes strategies, spreads, packs, bundles, and strips. |
| ETC | Exchange Traded Commodity | An exchange-traded product backed by commodity exposure. |
| ETF | Exchange Traded Fund | A fund traded on the exchange like a stock, tracking an index or basket of assets. |
| ETN | Exchange Traded Note | A debt instrument traded on exchange, tracking an underlying index or benchmark. |
| ETRF | Equity Total Return Futures | A subtype of TRF based on a single equity underlying. |
| European-style option | — | An option that can only be exercised at expiry. |
| Expiry / Expiry Date | — | The date on which an option or futures contract ceases to trade and settlement is determined. |
| FIS | TRF Forward Implied Spread | A strategy related to Total Return Futures combining an options or futures position with a forward component. |
| Flexible Instrument | — | A custom instrument created on-demand by a participant with non-standard parameters (e.g., non-standard expiry or exercise price). |
| Future | — | A standardized contract obligating the buyer to purchase (or seller to sell) an underlying asset at a specified future date at a predetermined price. |
| Futures Spread | — | A complex instrument of two futures legs on the same underlying but different expiry dates. Traded synthetically or directly. |
| Instrument | — | A tradeable entity on T7 — can be a simple (outright) instrument or a complex instrument (strategy). |
| Instrument Cover | — | A "cover" over a group of related instrument series (e.g., all strikes of one option expiry), used for certain trading controls. |
| IPS | Inter-Product Spread | A complex instrument spanning two different underlying products (e.g., TED spread). |
| ISIN | International Securities Identification Number | A 12-character alphanumeric code uniquely identifying a security globally (country code + national identifier + check digit). |
| Leg | — | A single component of a complex instrument. Each leg references a simple instrument with an associated ratio and side (Buy/Sell). |
| MIC | Market Identifier Code | A 4-character ISO code identifying a trading venue (e.g., `XEUR` = Eurex, `XETR` = Xetra, `XFRA` = Frankfurt). |
| NCSTR | Non-Standard Commodity Strip | A non-standard strip of commodity futures legs with irregular intervals. |
| NOS | Non-Standard Options Strategies | Complex options instruments with non-standard or user-defined leg structures. |
| NOVS | Non-Standard Options Volatility Strategies | Non-standard options strategies that include a futures/underlying leg. |
| Option | — | A contract giving the holder the right (but not the obligation) to buy (call) or sell (put) an underlying at a specific price on or before expiry. |
| OVS | Standard Options Volatility Strategies | Standard options strategies that include a futures/underlying leg for delta neutrality. |
| Pack | — | A complex instrument consisting of 4 consecutive quarterly futures contracts, used in interest rate futures. |
| PAG | Product Assignment Group | A grouping of products used for configuration and assignment of market parameters. |
| Product | — | A group of related instruments, e.g., a futures product family (DAX Futures). Instruments within a product share trading rules. |
| Put Option | — | An option granting the right to sell the underlying at the strike price. |
| Scaled Instrument | — | An instrument where prices are expressed in a scaled notation (e.g., dividend futures). |
| SCSPD | Standard Commodity Spread | A standard spread between commodity strips. |
| SCSTR | Standard Commodity Strip | A standard strip of commodity futures legs. |
| Series | — | A specific option contract identified by underlying, expiry, strike price, and call/put type. |
| Simple Instrument | — | A single-leg tradeable product — an outright future, option series, equity, ETF, etc. |
| SOS | Standard Options Strategies | Predefined complex options instruments with standard leg structures (e.g., straddles, strangles). |
| Spread | — | A complex instrument consisting of two opposite positions in related instruments (e.g., calendar spread = buy near-expiry / sell far-expiry). |
| Strategy | — | A complex instrument (multi-leg derivative structure), e.g., a futures spread, options straddle, or butterfly. |
| Strike Price | — | The fixed price at which the holder of an option can buy (call) or sell (put) the underlying. |
| Strip | — | A complex instrument consisting of a sequence of consecutive futures contracts, used in interest rate futures. |
| TED Spread | Treasury-EuroDollar Spread | An inter-product spread between government bond futures and short-term interest rate futures. |
| TRF | Total Return Futures | Futures contracts designed to replicate the total return of an underlying equity index including dividends. |
| Underlying | — | The asset (index, equity, commodity, interest rate) on which a derivative instrument is based. |
| Variance Futures | — | Futures contracts on the realized variance of an underlying index; traded with separate trading and clearing notations. |
| WKN | Wertpapierkennnummer | The German national securities identification number (6-character code). |

---

## Order Types & Attributes

| Abbreviation | Full Name | Definition |
|---|---|---|
| AVD / VDO | Auction Volume Discovery Order | An order type used during auctions to express interest in executing at the potential auction price; helps determine executable volume at the indicative auction price. |
| BBO Flag | Best Bid or Offer Setting Flag | An attribute on an order or quote indicating whether it set a new best bid or best ask price at the time of entry or price-modifying amendment. |
| BOC | Book-Or-Cancel | An order attribute requiring the order to be posted to the order book without any immediate execution; rejected if it would execute immediately. Also valid for quotes. |
| CAO | Closing-Auction-Only Order | An order that participates only in the closing auction; deleted if not executed by end of closing auction. |
| Cross Announcement | — | A notification to the market that a trader intends to execute buy and sell orders for the same instrument on behalf of different clients (cross trade). |
| Cross ID | — | An order attribute used with SMP Type A — orders with matching Cross IDs on the same side of the same BU will not match against each other. |
| Day Order | — | An order that expires at end of the trading day if not executed. Synonym for Good-for-Day (GFD). |
| FOK | Fill-Or-Kill | An order validity condition requiring the order to be fully executed immediately or cancelled entirely. No partial fills allowed. |
| GFD | Good-for-Day | An order validity that expires at end of the current trading day. Synonym for Day Order. |
| GTC | Good-Till-Cancelled | An order validity that keeps the order active in the book until it is fully executed or explicitly cancelled. Persists across trading sessions and days. |
| GTD | Good-Till-Date | An order validity that keeps the order active until a specified expiry date, after which it is automatically deleted. |
| IAO | Intraday-Auction-Only Order | An order that participates only in intraday auctions. |
| Iceberg Order | — | An order with a disclosed (peak) quantity and a hidden reserve quantity. Only the peak quantity is visible in the order book; replenished as executions occur. |
| IOC | Immediate-Or-Cancel | An order validity condition requiring the order to execute immediately (fully or partially) and cancel any unexecuted remainder. Never rests in the book. |
| Lean Order | — | A non-persistent order with restricted status message distribution — confirmations only sent to the submitting session. Cannot be GTD or GTC. |
| Limit Order | — | An order to buy or sell at a specified limit price or better. Rests in the order book if not immediately executable. |
| Limit Price | — | The price specified on a limit order; the worst acceptable execution price. |
| Market Order | — | An order to buy or sell at the best available price without a specified limit. Matched immediately against opposite book orders. |
| Mass Quote | — | A single message containing multiple quotes (bid/ask pairs) for many instruments simultaneously. |
| Midpoint Order | — | An order type that participates in midpoint matching (Xetra Midpoint service), executing at the midpoint of the current best bid/ask in the CLOB. |
| Midpoint Sweep Order | — | A midpoint order variant that first attempts midpoint book matching and then sweeps against the regular order book. |
| MTH Order | Main Trading Hours Order | An order that is valid only during the main trading hours window. |
| Multi Order FOK | — | A special order type allowing a set of orders to be submitted together with Fill-Or-Kill semantics applied across the entire set. |
| Non-Persistent Order | — | An order not stored in the database. Deleted on session disconnect, volatility interruption, or system restart. |
| OAO | Opening-Auction-Only Order | An order that participates only in the opening auction. |
| OCO | One-Cancels-the-Other Order | A pair of linked orders where the execution of one triggers the automatic cancellation of the other. Typically a stop order linked to a limit order. |
| Open-Close Indicator | — | A clearing-related attribute distinguishing whether a trade opens a new position or closes an existing one. |
| Peak Quantity | — | The disclosed (visible) quantity of an iceberg order. |
| Persistent Order | — | An order that is stored in the database and survives system restarts. Reloaded after recovery. |
| PWT Quote | Price-Without-Turnover Quote | A quote entered with a price indication but not intended for execution (used by Designated Sponsors in specific conditions). |
| Quote | — | A two-sided (bid and ask) price submission by a market maker or liquidity provider. Both sides managed together. |
| Rate Identifier | — | An attribute according to FIA guidelines, also known as Customer Order Handling Instruction, used in derivatives agency trades. |
| Reserve Quantity | — | The hidden quantity of an iceberg order, replenished to the peak size after each execution. |
| Stop Limit Order | — | A stop order that converts to a limit order upon triggering. |
| Stop Market Order | — | A stop order that converts to a market order upon triggering. |
| Stop Order | — | An initially inactive order that is triggered and converted to an active order (limit or market) when the market reaches the specified stop price. |
| Stop Price / Stop Limit | — | The trigger price for a stop order; when the market reaches this price, the stop order becomes active. |
| Take-Up Member | — | A clearing attribute identifying which clearing member takes up (assumes) the trade for clearing. |
| Trading Capacity | — | An order attribute identifying the business nature: Proprietary (P), Agency (A), Market Maker (M), Retail Liquidity Provision, Retail Agency, Riskless Principal (R), Issuer/LP. |
| TSO | Trailing Stop Order | A stop order where the stop price automatically adjusts by a defined trailing amount relative to market price movements. |

---

## Trading Concepts & Market Operations

| Abbreviation | Full Name | Definition |
|---|---|---|
| Aggressor | — | The incoming order that initiates a match against resting orders in the book. |
| Auction / Call Phase | — | A market phase where orders are collected without immediate matching; a single price is determined at the end that maximizes executable volume. |
| BBO | Best Bid and Offer | The best (highest) bid price and the best (lowest) ask price currently resting in the order book. |
| CLOB | Central Limit Order Book | The central order book in T7 for "lit" (displayed) on-book trading. All visible orders compete transparently. |
| CLIP | Client Liquidity Improvement Process | A special on-book service at Eurex (also known as Eurex Improve) allowing a firm to improve the price of a client order before exposing it to the market. |
| Closing Auction | — | An auction at the end of the trading day to determine a closing price. |
| Continuous Trading | — | A market phase in which incoming orders are continuously matched against resting book orders; any unmatched remainder stays in the book. |
| Cross Trade / Crossing | — | A trade between a buy and sell order entered by the same participant (or affiliated participants), subject to announcement and market exposure requirements. |
| Direct Matching | — | Matching of a complex instrument order directly against another complex instrument order (not decomposed into legs). |
| Dynamic Collar | — | A price range that adjusts dynamically based on recent trading activity; execution outside this range triggers a volatility interruption. |
| End-of-Day Processing | — | Automated processing at the close of the business day including deletion of expiring orders and settlement price determination. |
| Eurex Improve | Client Liquidity Improvement Process | See CLIP. A special on-book Eurex service allowing price improvement for client orders before market exposure. |
| Execution | — | The act of matching an order (fully or partially) resulting in a trade. |
| IEP / PAP | Indicative Equilibrium Price / Potential Auction Price | The price calculated during an auction that would maximize executable volume if uncrossing were to take place at that moment. T7 uses the term Potential Auction Price (PAP). |
| Intra-day Expiry | — | The expiry of an instrument during the trading day (rather than at end of day). |
| Intraday Auction | — | An auction triggered during the continuous trading day, e.g., after a volatility interruption. |
| Intraday Inactivation | — | The inactivation of an instrument mid-session. |
| Instrument Stop | — | An operator-controlled stop of trading for a specific instrument. |
| Instrument Suspension | — | A temporary halt of trading in a specific instrument (instrument state Suspended). |
| Knock-Out | — | An instrument state indicating the instrument has been knocked out (e.g., for structured products), making it no longer tradeable in normal fashion. |
| Leg Execution Price | — | The individual price assigned to each leg of a complex instrument upon execution. |
| Locked Stock (LS) | — | A state in the Continuous Auction with Specialist trading model where orders are temporarily frozen during a freeze phase. |
| MAQ | Minimum Acceptable Quantity | An execution condition for midpoint orders specifying the minimum partial fill quantity acceptable. |
| Match / Matching | — | The process by which compatible buy and sell orders are paired and a trade is created. |
| MMP | Market Maker Protection | A configurable protection mechanism automatically deactivating a market maker's quotes if a defined number of executions or cumulative volume threshold is breached within a defined time window. |
| Net Price | — | The net price of a complex instrument order, calculated from the leg prices. |
| Off-book | — | Trading functionality not involving the central order book; includes TES, Eurex EnLight (SRQS), and basket trading. |
| On-book | — | Trading functionality of the central order book (CLOB); orders matched by the matching engine. |
| Opening Auction | — | An auction held at the start of the trading day before continuous trading begins, to establish the opening price. |
| Order Book | — | The electronic ledger of all outstanding (resting) buy and sell orders for an instrument, ranked by price and time priority. |
| Passive / Book Order | — | The resting order(s) in the book that are matched against an incoming aggressor. |
| PLP | Passive Liquidity Protection | A mechanism that prevents aggressive orders from executing against resting orders from the same Business Unit under certain conditions. |
| Potential Auction Price (PAP) | — | The auction price calculated during an auction call that maximizes executable volume. See also IEP. |
| Price-Time Priority | — | The standard order allocation method: orders at better prices are matched first; at equal price, earlier-arriving orders have priority. |
| Pro-Rata Allocation | — | An order allocation method where execution quantity is distributed proportionally across all orders at the same price level. |
| QRS | Quote Request Solution | A mechanism allowing a market maker to express a price in response to an RfQ, and for the requester to trade against that quote. |
| Request for Quote (RfQ) | — | A mechanism allowing a trader to request quotes from market makers for a specific instrument, typically when there is no sufficient visible market. |
| SMP | Self-Match Prevention | A feature preventing orders/quotes from the same Business Unit (or same Cross ID group) from matching against each other. Available as Type A (Cross ID-based) and Type B (session-based). |
| Sold-Out | — | An instrument state indicating all available supply has been sold, applicable to warrant-like products. |
| Static Collar | — | A fixed price range defined around the reference price; execution outside this range triggers a volatility interruption. |
| Synthetic Matching | — | Matching of complex instrument (strategy/spread) orders against combinations of simple instrument orders, allowing execution even when no direct complex instrument counterpart exists. Also called Implied Matching. |
| TAC | Trade-at-Close | An instrument phase (used for TRF) during which trading occurs at the closing reference price. |
| TAL | Trade-at-Last | A matching mode in which orders are matched at the last trade price during specific instrument phases. |
| Time-Pro-Rata Allocation | — | An allocation method combining time priority and pro-rata; a minimum fill is guaranteed to the best-priced order. |
| Trade | — | The result of a successful match between a buy order and a sell order at an agreed price and quantity. |
| Trade Reversal | — | The cancellation of a previously executed trade, e.g., due to an erroneous trade. |
| Uncrossing | — | The process of determining and executing trades at the end of an auction phase based on the Potential Auction Price. |
| VI | Volatility Interruption | An automatic suspension of continuous trading triggered when a potential execution price falls outside the permitted price corridor (static or dynamic collar). Trading resumes after an auction call phase. |
| VWAP | Volume-Weighted Average Price | The average price of a security weighted by volume traded over a given period. Used as a benchmark in execution quality assessment. |
| Xetra Midpoint | — | A service on Xetra allowing execution at the midpoint of the current CLOB best bid/ask price via a dedicated midpoint order book. |
| Xetra Retail Execution (XRE) | — | A special service providing retail investors (RMO orders) with price improvement via Retail Liquidity Provider (RLP) quotes. |

---

## Protocols & Interfaces

| Abbreviation | Full Name | Definition |
|---|---|---|
| Broadcast Connection | — | A separate ETI connection used to receive asynchronous push notifications (execution reports, order book updates). |
| ClOrdID | Client Order ID | FIX tag 11 — a unique order identifier assigned by the client, max 20 characters. |
| DeleteAllQuoteRequest | — | ETI message to cancel all quotes for a product/instrument. |
| DeleteOrderRequest | — | ETI message to cancel a specific order. |
| EMDI | Extended / Enhanced Market Data Interface | T7's enhanced version of MDI with additional price levels and information. |
| EMDS | Extended Market Data Service | T7's extended market data service providing additional data beyond EMDI. |
| EOBI | Enhanced Order Book Interface | T7's primary public market data interface. Delivers the full visible order book in real-time, order-by-order, via multicast UDP binary protocol. |
| ETI | Enhanced Transaction Interface | T7's primary binary order entry protocol. High performance, low latency, session-based. Used directly or as the backend for FIX LF. Repos: `eurex/gateway/eti`. |
| ExecutionReport | — | FIX/ETI message notifying participants of order state changes (new, fill, cancel, reject). |
| FIX / FIX LF | Financial Information eXchange / Low Frequency Gateway | T7's FIX protocol adapter based on FIX 5.0 SP2. A secondary order entry interface for participants who cannot use ETI directly. |
| FullOrderExecution | — | EOBI message for a fully executed order. |
| GUI | Graphical User Interface | T7's browser-based trading and administration interface for manual trading, monitoring, and operations. |
| HeartBeat | — | A periodic keep-alive message exchanged between participant and T7 to maintain session liveness. |
| InstrumentSummary | — | EOBI snapshot message of instrument-level state. |
| Logon | — | The session establishment message to start an ETI or FIX session. |
| MassQuoteRequest | — | ETI message to submit multiple quotes (bid/ask pairs) simultaneously. |
| MDI | Market Data Interface | T7's netted, price-level-aggregated market data interface. Provides best-bid/ask and market depth in netted form. |
| ModifyOrderRequest | — | ETI message to amend (modify) an existing order. |
| NewOrderRequest | — | ETI message to submit a new order to T7. |
| OrderAdd | — | EOBI message indicating a new order or quote side has been added to the book. |
| OrderCancelReject | — | FIX message indicating that a cancel or amend request was rejected. |
| OrderDelete | — | EOBI message indicating an order has been removed (cancelled/expired). |
| OrderID | Exchange Order ID | The unique order identifier assigned by T7's exchange system. |
| OrderMassDelete | — | EOBI message for bulk deletion of orders (e.g., on session disconnect). |
| OrderModify | — | EOBI message indicating an order's price or quantity has been amended. |
| PacketHeader | — | EOBI message providing sequence number and timestamp for each multicast packet. |
| PartialOrderExecution | — | EOBI message for a partially executed order. |
| ProductSummary | — | EOBI snapshot message of product-level state. |
| RDA | Reference Data Access / Propagation | Internal architecture for distributing reference data from RDS to components within T7. |
| RDF | Reference Data File | Static file-based reference data distribution (daily file feed for participants). |
| RDI | Reference Data Interface | T7's interface for distributing instrument and product reference data to external participants. |
| RetransmitRequest | — | ETI message allowing participants to request re-delivery of missed messages from a specific sequence range. |
| SecurityID | — | FIX tag 48 — identifies the instrument (T7 uses SecurityID + SecurityIDSource). |
| SessionID | — | Unique identifier for an ETI or FIX session. |
| SRQSDealNotification | — | ETI message notifying participants of a deal struck in an SRQS negotiation. |
| SRQSOpenNegotiationRequest | — | ETI message to open a Selective RfQ (Eurex EnLight) negotiation event. |
| Subscribe | — | ETI message to register for broadcast notifications (e.g., order book updates, trade notifications). |
| TESApproveTrade | — | ETI message for counterparty approval of a TES trade. |
| TESNewTradeRequest | — | ETI message to initiate a TES (off-book) trade. |
| WSS | Web Service / Web Socket Service | T7 interfaces for control data and report access via web services. |

---

## Risk & Clearing

| Abbreviation | Full Name | Definition |
|---|---|---|
| ARP | Advanced Risk Protection | An enhanced risk protection layer providing multi-level breach responses (soft/hard stops, optional order deletion). |
| CCP | Central Counter Party | A clearing institution (e.g., Eurex Clearing AG) that interposes itself between buyer and seller, guaranteeing settlement. |
| Clearing Account | — | The account at the CCP to which a cleared trade is attributed. |
| Clearing Member Stop of Trading Participant | — | An action by a CM to stop trading for a DC/NCM participant they are responsible for. |
| ECAG | Eurex Clearing AG | The central counterparty clearing house for Eurex. |
| Initial Margin | — | Margin deposited when a position is opened. |
| Kill Switch / EMD | Emergency Mass Deletion | A risk control mechanism allowing immediate deletion of all open orders and quotes for a BU or participant. Can be triggered by the participant, CM, or exchange. |
| LEI | Legal Entity Identifier | A 20-character alphanumeric identifier for legal entities participating in financial transactions (used in MiFID II reporting). |
| Margin | — | Collateral deposited with the CCP to cover potential future losses on open derivatives positions. |
| Margin-Based Risk Limit | — | A risk limit expressed in terms of margin exposure rather than order quantity or value. |
| Maximum Order Quantity | — | A configurable per-user limit on the maximum quantity of a single order. |
| Maximum Order Value | — | A configurable per-user limit on the maximum notional value of a single order. |
| MiFID II / MiFIR | Markets in Financial Instruments Directive II / Regulation | EU regulation governing financial markets; imposes extensive transaction reporting, pre-trade transparency, and best execution requirements. T7 supports MiFID II fields. |
| OTC | Over-the-Counter | Trading conducted directly between two parties, outside of an exchange order book. |
| Preliminary Clearing Price | — | An intraday clearing price published before final settlement, used for preliminary TRF trade valuations. |
| Prisma | — | Eurex Clearing's risk-based margin methodology (Portfolio-based Risk Management). |
| Settlement Price | — | The official closing price used for daily margin calculations and final settlement. |
| SI | Settlement Institution | The institution responsible for delivering/receiving securities and cash in settlement of a trade. |
| TAM | Trade at Market | A TES trade type for Total Return Futures where one side trades at the current market price. |
| Trader / BU Stop | — | An operator or CM action that suspends all trading activity for a specific trader or BU, with mass deletion of open orders. |
| Transaction Size Limit | — | An exchange-defined maximum per-order size (quantity or value) for a product and BU combination. |
| Variation Margin | — | Daily mark-to-market cash flows reflecting gains and losses on open positions. |

---

## Operational Terms

| Abbreviation | Full Name | Definition |
|---|---|---|
| ActiveMQ | — | Java-based messaging broker used for JBoss/Java-tier components in T7. |
| BSE | Bulgarian / Budapest Stock Exchange | Either the Bulgarian Stock Exchange or Budapest Stock Exchange (a Vienna partner exchange operating on T7). |
| Business Day | — | The trading day on T7; begins with pre-trading preparation and ends with end-of-day processing. |
| CMDB | Configuration Management Database | T7's internal database recording application types, process topology, and component metadata. |
| DBAG | Deutsche Börse AG | The parent holding company of Deutsche Börse Group. |
| EEX | European Energy Exchange | An energy derivatives exchange operating on T7. |
| Eurex | — | Deutsche Börse's derivatives exchange, operated on T7. MIC: `XEUR`. |
| FIA | Futures Industry Association | Industry association for exchange-traded derivatives; defines the Rate Identifier (Customer Order Handling Instruction) standard. |
| Frankfurt | — | Frankfurt Stock Exchange's floor-based venue (Deutsche Börse Frankfurt), operated on T7. MIC: `XFRA`. |
| Halt | — | A product state suspending all trading activity across all instruments in a product. |
| Infoscreen | — | An operational display service providing market state information. |
| Instrument State | — | The lifecycle state of a specific tradeable instrument (e.g., `Book`, `Continuous`, `Auction`, `Freeze`, `Closed`, `Restricted`, `Suspended`, `Knock-Out`, `Expired`). |
| Lot Size | — | The minimum tradeable quantity for a given instrument (minimum order size). |
| MSE | Malta Stock Exchange | A cash market exchange operating on T7. |
| NATS | — | A lightweight messaging infrastructure used in newer T7 components alongside the internal messaging bus. |
| NTA | Network Time Authority | The time server providing synchronized timestamps to all T7 components. |
| Product State | — | The lifecycle state of a product group (e.g., `Pre-Trading`, `Trading`, `Post-Trading`, `End-of-Day`, `Closed`, `Halt`, `Prepare`, `Ready`). |
| Segment MIC | — | The MIC identifying the trading segment (venue segment) associated with a specific TES trade for reporting purposes. |
| SOAP | Simple Object Access Protocol | A web service protocol used for some T7 administrative interfaces (monitoring, reference data). |
| Tick Size | — | The minimum price increment for a given instrument; defined per instrument in reference data. |
| WBAG | Vienna Stock Exchange | The Vienna Stock Exchange and its partner exchanges (Budapest BSE, Prague PSE, Ljubljana LJSE, Zagreb ZSE), operated on T7. MIC: `XVIE`. |
| Xetra | — | Frankfurt Stock Exchange's primary electronic trading venue (Deutsche Börse Xetra), operated on T7. MIC: `XETR`. |

---

## TES & Off-Book Trading

| Abbreviation | Full Name | Definition |
|---|---|---|
| Auto-Approval | — | A TES feature where the submitting participant's side is automatically approved without manual action. |
| Bilateral TES Trade | — | A TES trade between exactly two counterparties (one buyer, one seller). |
| Block Trade | — | A large off-book trade entered via TES, typically above a minimum quantity threshold defined per product. |
| EFP | Exchange for Physical | A TES trade type where a futures position is exchanged for the corresponding physical (cash) position. |
| EFS | Exchange for Swaps | A TES trade type where a futures position is exchanged for an OTC swap. |
| Multilateral TES Trade | — | A TES trade with multiple sides (counterparties), e.g., in a give-up scenario. |
| Non-Disclosure Limit | — | A TES parameter specifying above which size a trade is published immediately vs. with a publication delay. |
| TES Profile | — | A set of configurable parameters per product/expiry defining TES trade rules (minimum size, publication delay, allowed types). |
| TES Side | — | One participant's leg in a TES trade — defines the counterparty, quantity, price, and clearing info for that participant. |
| TES State | — | The lifecycle state of a TES trade (e.g., Pending Approval, Approved, Deleted). |
| TES Trade | T7 Entry Service Trade | An off-book trade entered via TES, comprising multiple TES sides (counterparties) that must mutually approve the trade. |
| TES Type | — | Classification of a TES trade by regulatory or commercial category (e.g., Block Trade, EFP, EFS, VOLA, TAM). |
| Time of Commencement | — | A TES attribute recording when trade negotiation began (for regulatory purposes). |
| VOLA Strategy | — | A TES trade type combining an options strategy with a delta-hedging futures leg. |

---

## Eurex EnLight / SRQS

| Abbreviation | Full Name | Definition |
|---|---|---|
| AutoEx | Auto Execution | An SRQS feature enabling automatic execution of deals matching pre-defined price conditions without manual confirmation. |
| Deal | — | The agreed trade resulting from an SRQS negotiation where Requester accepts a Respondent's quote. |
| Eurex EnLight | — | The SRQS service on the Eurex derivatives market. Enables bilateral and multilateral off-book price negotiation. |
| Negotiation Event | — | A single SRQS workflow instance initiated by a Requester to seek quotes from Respondents for a specific instrument and quantity. |
| Requester | — | The participant initiating an SRQS negotiation event by sending a Request for Quote. |
| Respondent | — | A participant invited to respond to an SRQS negotiation event with a quote. |
| SMART RfQ | — | An automated SRQS feature that selects the best available respondents for a negotiation event based on predefined criteria. |
| SRQS | Selective Request for Quote Service | T7's electronic negotiation service for off-book trades. Branded as Eurex EnLight (derivatives) and Xetra EnLight (cash). |
| Working Delta Negotiation | — | An SRQS workflow for options strategies where the delta hedge is negotiated dynamically as part of the deal. |
| Xetra EnLight | — | The SRQS service on the Xetra cash market. |

---

## Document Types & Regulatory Abbreviations

| Abbreviation | Full Name | Definition |
|---|---|---|
| BRA | Business Requirements Analysis | T7 document type for business requirements. |
| DFS | Detailed Functional Specification | T7 document type providing detailed functional requirements and specifications (prefixed DFS + number, e.g., DFS10070). |
| DTS | Design / Technical Specification | T7 document type for internal design specifications (prefixed DTS + number). |
| ESMA | European Securities and Markets Authority | EU financial markets regulator; defines MiFID II reporting field requirements implemented in T7. |
| MFG | Market Functional Guide | T7 document type providing market-facing functional guidance (prefixed MFG + number, e.g., MFG141002). |
| MTD | Manual / Technical Document | T7 document type for technical and interface reference manuals (prefixed MTD + number). |
| NBBO | National Best Bid and Offer | The best bid/offer prices aggregated across all trading venues. Primarily a US concept; in T7/Xetra context the equivalent is BBO — the best prices within the T7 CLOB. |
| SIR | System Incident Report | T7 document type for post-incident analysis. |
| SRA | System Requirements Analysis | T7 document type for high-level functional difference analysis. |
| SRQ | System Requirements | T7 document type for system-level requirements (prefixed SRQ + number). |

---

## Codebase Search Term Mappings

Use this reference to translate natural-language query concepts into effective T7 codebase
search terms. When a query uses a general word, look up the T7-specific equivalent here
before searching.

### Release naming

If a release is requested then use the following mapping.
E.g. 14.0 maps to `140.000.000`, 15.0 maps to `150.000.000`, 15.1 maps to `151.000.000`, and so on.
The mapping is not one-to-one, so if the query references a release that does not have a direct mapping, use the closest release. For example for 14.0 it can be 140.001.000 or 140.002.000, for 15.1 it can be 151.001.000, and so on.

### Order Types

| Concept | T7 Terms to Search |
|---------|-------------------|
| Limit order | `limit_order`, `LimitOrder`, `order_type_limit` |
| Market order | `market_order`, `MarketOrder`, `order_type_market` |
| Stop order | `stop_order`, `StopOrder`, `stop_trigger` |
| Iceberg / disclosed quantity | `iceberg`, `disclosed_qty`, `peak_qty`, `MaxFloor` |
| Midpoint order | `midpoint`, `MidpointOrder`, `midpoint_price`, `midpoint_matching` |
| Persistent order | `persistent`, `PersistentOrder`, `order_persistence` |
| Non-persistent order | `non_persistent`, `session_order`, `day_order` |
| Good-till-cancelled | `GTC`, `good_till_cancelled`, `order_validity_gtc` |
| Good-till-date | `GTD`, `good_till_date`, `expiry_date` |
| Immediate-or-cancel | `IOC`, `immediate_or_cancel`, `validity_ioc` |
| Fill-or-kill | `FOK`, `fill_or_kill`, `validity_fok` |
| One-cancels-other | `OCO`, `one_cancels_other` |

### Matching

| Concept | T7 Terms to Search |
|---------|-------------------|
| Matching algorithm | `matching_algorithm`, `MatchingAlgorithm`, `match_type` |
| Price determination | `price_determination`, `execution_price`, `uncrossing_price` |
| Order book sweep | `sweep`, `book_sweep`, `aggressive_order` |
| Auction / call phase | `auction`, `call_phase`, `indicative_price`, `IEP` |
| Opening auction | `opening_auction`, `opening_uncrossing` |
| Intraday auction | `intraday_auction`, `volatility_interruption` |
| Closing auction | `closing_auction`, `closing_price` |
| Continuous trading | `continuous_trading`, `continuous_matching` |
| Order priority | `order_priority`, `time_priority`, `price_priority`, `pro_rata` |
| Trade-at-last | `trade_at_last`, `TAL`, `reference_price_matching` |
| Volatility interruption | `volatility_interruption`, `VI`, `dynamic_collar`, `static_collar` |
| Extended hours | `extended_hours`, `pre_trading`, `post_trading` |

### Instruments

| Concept | T7 Terms to Search |
|---------|-------------------|
| Instrument state | `instrument_state`, `InstrumentState`, `trading_state` |
| Market state | `market_state`, `MarketState`, `session_state` |
| Product group | `product_group`, `ProductGroup` |
| Complex instrument | `complex_instrument`, `strategy`, `leg` |
| Options on futures | `option`, `OptionOnFuture`, `exercise`, `expiry` |
| Futures | `future`, `FutureInstrument`, `settlement` |
| Cash equities | `equity`, `share`, `cash_instrument` |
| ETF | `ETF`, `exchange_traded_fund` |
| Reference price | `reference_price`, `last_traded_price`, `settlement_price` |
| Strike price | `strike`, `StrikePrice`, `exercise_price` |

### Risk

| Concept | T7 Terms to Search |
|---------|-------------------|
| Pre-trade risk check | `pre_trade_risk`, `PATE`, `risk_check` |
| Risk limit | `risk_limit`, `RiskLimit`, `max_order_value` |
| Kill switch | `kill_switch`, `KillSwitch`, `emergency_mass_delete` |
| Position limit | `position_limit`, `net_position` |
| Business unit | `business_unit`, `BusinessUnit`, `BU` |
| Clearing member | `clearing_member`, `CM`, `clearing` |

### Protocols

| Concept | T7 Terms to Search |
|---------|-------------------|
| New order request | `NewOrderRequest`, `new_order`, `order_entry` |
| Order modification | `ModifyOrderRequest`, `order_modify`, `amend` |
| Order cancellation | `DeleteOrderRequest`, `order_cancel`, `delete_order` |
| Mass cancellation | `mass_delete`, `MassDelete`, `cancel_all` |
| Execution report | `ExecutionReport`, `execution_report`, `fill_report` |
| Order book update | `order_book_update`, `ObUpdate`, `depth_update` |
| Trade confirmation | `trade_confirmation`, `TradeConfirmation` |
| Heartbeat | `heartbeat`, `Heartbeat`, `session_keepalive` |
| Logon / session | `Logon`, `session_logon`, `ETI_logon`, `FIX_logon` |
| Throttle | `throttle`, `rate_limit`, `order_rate` |

### TES

| Concept | T7 Terms to Search |
|---------|-------------------|
| TES trade | `tes_trade`, `TesTouch`, `off_book_trade` |
| TES approval | `tes_approval`, `TesApproval`, `counterparty_approval` |
| TES side | `tes_side`, `TesSide`, `buyer_seller` |
| TES state | `tes_state`, `TesState`, `pending_approval` |
| Block trade | `block_trade`, `BlockTrade` |
| Eurex Trade Entry | `ETE`, `eurex_trade_entry` |

### Configuration

| Concept | T7 Terms to Search |
|---------|-------------------|
| Partition configuration | `partition_config`, `PartitionConfig`, `commondb.Partition` |
| Pool configuration | `pool_config`, `PoolConfig`, `server_pool` |
| Market parameters | `market_params`, `MarketParameters`, `trading_parameters` |
| Price collar | `price_collar`, `PriceCollar`, `collar_range` |
| Tick size | `tick_size`, `TickSize`, `minimum_price_increment` |
| Lot size | `lot_size`, `LotSize`, `minimum_quantity` |
