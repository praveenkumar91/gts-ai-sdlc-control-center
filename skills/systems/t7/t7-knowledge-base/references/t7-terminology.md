# T7 Domain Terminology

Use this reference to translate natural-language query concepts into effective T7 codebase
search terms. When a query uses a general word, look up the T7-specific equivalent here
before searching.

---

## Release naming

If a release is requested then use the following mapping.
E.g. 14.0 maps to `140.000.000`, 15.0 maps to `150.000.000`, 15.1 maps to `151.000.000`, and so on.
The mapping is not one-to-one, so if the query references a release that does not have a direct mapping, use the closest release. For example for 14.0 it can be 140.001.000 or 140.002.000, for 15.1 it can be 151.001.000, and so on.


## Order Types and Properties

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

---

## Matching and Price Discovery

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

---

## Instrument and Product Concepts

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

---

## Risk and Pre-Trade Controls

| Concept | T7 Terms to Search |
|---------|-------------------|
| Pre-trade risk check | `pre_trade_risk`, `PATE`, `risk_check` |
| Risk limit | `risk_limit`, `RiskLimit`, `max_order_value` |
| Kill switch | `kill_switch`, `KillSwitch`, `emergency_mass_delete` |
| Position limit | `position_limit`, `net_position` |
| Business unit | `business_unit`, `BusinessUnit`, `BU` |
| Clearing member | `clearing_member`, `CM`, `clearing` |

---

## Protocols and Messages

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

---

## TES (Trade Entry Service)

| Concept | T7 Terms to Search |
|---------|-------------------|
| TES trade | `tes_trade`, `TesTouch`, `off_book_trade` |
| TES approval | `tes_approval`, `TesApproval`, `counterparty_approval` |
| TES side | `tes_side`, `TesSide`, `buyer_seller` |
| TES state | `tes_state`, `TesState`, `pending_approval` |
| Block trade | `block_trade`, `BlockTrade` |
| Eurex Trade Entry | `ETE`, `eurex_trade_entry` |

---

## Configuration Parameters

| Concept | T7 Terms to Search |
|---------|-------------------|
| Partition configuration | `partition_config`, `PartitionConfig`, `commondb.Partition` |
| Pool configuration | `pool_config`, `PoolConfig`, `server_pool` |
| Market parameters | `market_params`, `MarketParameters`, `trading_parameters` |
| Price collar | `price_collar`, `PriceCollar`, `collar_range` |
| Tick size | `tick_size`, `TickSize`, `minimum_price_increment` |
| Lot size | `lot_size`, `LotSize`, `minimum_quantity` |
