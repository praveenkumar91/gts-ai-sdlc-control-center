# T7 Application Types

All application types registered in `CMDB.ApplicationType`, mapped to their T7 component(s).

> Source: `SELECT * FROM CMDB.ApplicationType ORDER BY ApplicationTypeId` — queried 2026-05-20.

---

## Core Trading

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 2 | MatchingEngine | Me | Matcher | Tier | MESSAGING | `eurex/apps/matcher`, `eurex/apps/matcherexternal`, `eurex/apps/matchergwval`, `eurex/intmsg/model/matcher` |
| 53 | TradeEntryService | Tes | Tes | Tier | MESSAGING | `eurex/apps/trade-entry-service`, `eurex/apps/tesgwval`, `eurex/dataaccess/tradeentryservice`, `eurex/intmsg/model/tradeentryservice` |
| 41 | PostProcessorTradingEngine | PaTe | PaTe | Tier | MESSAGING | `eurex/apps/pate` |
| 58 | LiquidityDiscoveryService | Lds | Lds | Tier | MESSAGING | `eurex/apps/liquidity-discovery-service`, `eurex/apps/ldsgwval`, `eurex/intmsg/model/liquidity-discovery-service` |
| 56 | OrderDropCopyService | Odcs | Odcs | Tier | MESSAGING | `eurex/apps/odcserver`, `eurex/gateway/odcgw`, `eurex/gateway/odcgwconversion`, `eurex/intmsg/model/odc` |

---

## Gateways

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 54 | GatewayFIX | GwFIX | GatewayFIX | Tier | MESSAGING | `eurex/gateway/fixgw`, `eurex/gateway/fix`, `eurex/gateway/fixgwconversion`, `eurex/intmsg/model/fixgw` |
| 55 | GatewayLF | GwLF | GatewayLF | Singleton | MESSAGING | `eurex/gateway/gateway`, `eurex/gateway/eti`, `eurex/gateway/gwconversion`, `eurex/intmsg/model/gateway` |
| 57 | GatewayODC | GwODC | GatewayODC | Singleton | MESSAGING | `eurex/gateway/odcgw`, `eurex/gateway/odcgwconversion`, `eurex/intmsg/model/odc` |
| 78 | GatewayGSE | GwGSE | GatewayGSE | Tier | MESSAGING | `eurex/apps/fagse`, `eurex/gateway/common` |
| 7 | OutboundFeedInterface | Ofi | Ofi | Singleton | MESSAGING | `eurex/gateway/outboundfi`, `eurex/gateway/oficonversion`, `eurex/intmsg/model/outboundfi` |
| 1002 | ConnectionTestGateway | CTestGw | CnctTestGw | NoTier | HOCO | `eurex/apps/connection-test-gateway` |

---

## Market Data

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 44 | MarketDataInterface | Mdi | Mdi | Tier | MESSAGING | `eurex/apps/market-data-obo-incremental`, `eurex/apps/market-data-netted`, `eurex/apps/multicaster` |
| 49 | InternalMarketDataInterface | IMdi | IMdi | Tier | MESSAGING | `eurex/apps/market-data-obo-incremental`, `eurex/apps/market-data-netted` |
| 46 | PriceFeedHandler | Pfh | PriceFeedHandler | Tier | MESSAGING | `eurex/apps/market-data-netted`, `eurex/apps/market-data-republisher` |
| 43 | TradeFeedHandler | Tfh | TradeFeedHandler | Tier | MESSAGING | `eurex/apps/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler`, `eurex/intmsg/model/trade-feed-handler-internal` |
| 45 | MarketDataHeartbeat | Mdh | Mdh | NoTier | MESSAGING | `eurex/apps/market-data-heartbeat` |
| 1003 | ConnectionTestMarketDataHeartbeat | CTstMdh | CnctTestMdh | NoTier | MESSAGING | `eurex/apps/market-data-heartbeat` |

---

## Reference Data

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 28 | ReferenceDataDistributor | Rdd | Rdd | Tier | MESSAGING | `eurex/apps/reference-data-distributor`, `eurex/intmsg/model/referencedata` |
| 16 | ReferenceDataBridge | RefBrdg | RefDataBridge | Tier | MESSAGING | `eurex/dataaccess/rda-outbound-bridge`, `common/dataaccess/rda-outbound-bridge-common`, `common/dataaccess/rdc` |
| 25 | RdaInboundBridge | Rib | RdaInboundBridge | Tier | MESSAGING | `common/dataaccess/rda-inbound-bridge` |
| 38 | RDS | RDS | RDS | JBossTier | SOAP | `eurex/apps/refdata`, `eurex/apps/refdata-application`, `eurex/apps/refdata-database`, `common/dataaccess/rdc` |

---

## Controller / Monitor / Infrastructure

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 9 | SystemController | SCS | SystemController | Tier | MESSAGING | `common/controller-monitor/bos`, `eurex/common/controller-monitor/bos` |
| 10 | SystemMonitor | MON | SystemMonitor | Tier | MESSAGING | `common/controller-monitor/monitor`, `eurex/common/controller-monitor/session` |
| 14 | MonitorStateCalculator | MSC | MonitorStateCalculator | Tier | MESSAGING | `common/controller-monitor/monitorstatecalc` |
| 18 | SessionManager | Sem | SessionManager | Tier | MESSAGING | `eurex/common/controller-monitor/session` |
| 19 | HostController | Hc | HostController | NoTier | HOCO | `common/controller-monitor/host` |
| 20 | StatusManager | STTS | StatusManager | Tier | MESSAGING | `common/controller-monitor/status` |
| 22 | MonitorSoapInterface | MSI | MonitorSoapInterface | Tier | MESSAGING | `common/controller-monitor/monitorsoap`, `common/controller-monitor/monitorsoapconnector`, `eurex/common/controller-monitor/monitorsoap` |
| 26 | MonitorSNMPInterface | MSNMP | MonitorSNMPInterface | Tier | MESSAGING | `common/controller-monitor/monitorsnmp` |
| 50 | InfoscreenAdaptor | ISAdapt | InfoscreenAdaptor | Tier | MESSAGING | `eurex/common/controller-monitor/infoscreenadaptor` |
| 71 | JobScheduler | JSched | JobScheduler | Tier | MESSAGING | `common/controller-monitor/bos` |
| 75 | JobSchedulerGui | JSGui | JobSchedulerGui | Tier | MESSAGING | `common/controller-monitor/opcon`, `eurex/common/controller-monitor/opcon` |
| 76 | JobSchedulerCtrl | JSCtrl | JobSchedulerCtrl | Tier | MESSAGING | `common/controller-monitor/opcon`, `eurex/common/controller-monitor/opcon` |

---

## Performance Monitor

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 11 | PerformanceMonitor | PERF | PerformanceMonitor | NoTier | MESSAGING | `common/perfmon`, `perfmon/core` |
| 23 | PerformanceLogger | PML | PerformanceLogger | NoTier | MESSAGING | `perfmon/core`, `perfmon/capture` |
| 24 | PerformanceCalculator | PerCal | PerformanceCalculator | NoTier | MESSAGING | `perfmon/core`, `perfmon/ackstat` |
| 35 | PerformanceGUI | PerfGUI | PerformanceGUI | NoTier | HOCO | `common/perfmon` |
| 39 | PerfPcapProxy | PerPcap | PerfPcapProxy | NoTier | HOCO | `perfmon/capture` |
| 40 | PerfMonSOAPProxy | PerfMS | PerfMonSOAPProxy | NoTier | HOCO | `perfmon/monsoapproxy` |
| 47 | PerfPMsgRouter | PPMR | PerfPMsgRouter | Tier | MESSAGING | `perfmon/core`, `common/perfmon` |
| 48 | PerfOMsgRouter | POMR | PerfOMsgRouter | Tier | MESSAGING | `perfmon/core`, `common/perfmon` |
| 52 | PerfEMsgRouter | PEMR | PerfEMsgRouter | NoTier | MESSAGING | `perfmon/core`, `common/perfmon` |
| 59 | PerfLoggerServer | PerLogS | PerfLoggerServer | NoTier | HOCO | `perfmon/capture` |
| 77 | PerfPcapDecoder | PerPDec | PerfPcapDecoder | Tier | SOAP | `perfmon/capture`, `perfmon/ipasm` |

---

## Misc / Other Application Services

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 15 | NewsService | News | NewsService | Tier | MESSAGING | `eurex/apps/newsservice` |
| 17 | ContractManager | CoMa | ContractManager | JBossTier | SOAP | `eurex/apps/contractmanager`, `eurex/apps/contractmanager-comm`, `eurex/intmsg/model/contractmanager` |
| 42 | MessageDumpFacility | Mdf | Mdf | NoTier | MESSAGING | `common/controller-monitor/archservice` |
| 29 | TimerControlFacility | Tcf | Tcf | Singleton | MESSAGING | `common/controller-monitor/bos` |

---

## Market Data Recording (MDR)

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 79 | MDRCombo | MDRComb | MDRCombo | Tier | SOAP | MDR infrastructure (external tooling, separate from core T7 C++ codebase) |
| 80 | MDRCosher | MDRCosh | MDRCosher | Tier | HOCO | MDR infrastructure |

---

## Database / Messaging Infrastructure

| ID | Name | ShortName | ProcessName | TierType | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------|----------------|--------------|
| 4 | LocalMySQL | lsql | LocalMySQL | NoTier | HOCO | `eurex/dataaccess/mysql-configurations`, `common/dataaccess/mysql-scripts-common` |
| 37 | ActiveMQ | ActMQ | ActiveMQ | JBossTier | HOCO | `common/amqp`, `common/amqp-qpid` |
| 82 | NatsServer | NatsSrv | NatsServer | NoTier | HOCO | NATS messaging infrastructure (external, not in T7 source) |
| 27 | CentralRsyslog | CRsys | CentralRsyslog | Tier | SOAP | OS-level rsyslog infrastructure |
| 30 | Rsyslog | Rsys | Rsyslog | NoTier | HOCO | OS-level rsyslog infrastructure |
| 1000 | ClusterDB | CluDB | ClusterDatabase | JBossTier | HOCO | `common/controller-monitor/database`, `eurex/common/controller-monitor/database` |
| 1001 | HAMySQL | HAMySQL | HAMySQL | Tier | MESSAGING | `eurex/dataaccess/mysql-configurations` |

---

## Live Results (LR) — ApplicationTypeGroup 3

All LR application types use `LRTier` and multicast-based partitioning (`PartitionType=2`).

| ID | Name | ShortName | ProcessName | MonitoringType | Component(s) |
|----|------|-----------|-------------|----------------|--------------|
| 101 | LRDataNode | LRData | LR#pDataNode | MESSAGING | `common/GMC` — Live Results cluster data node |
| 102 | LRControllerNode | LRCtrl | LR#pControllerNode | MESSAGING | `common/GMC` — Live Results cluster controller |
| 103 | LRRDBMutator | LRRdb | LR#pRDBMutator | MESSAGING | `common/GMC` — Live Results RDB mutator |
| 104 | LRCoMaMutator | LRCoMa | LR#pCoMaMutator | MESSAGING | `common/GMC` — Live Results ContractManager mutator |
| 106 | LRMDIMutator | LRMdi | LR#pMDIMutator | MESSAGING | `common/GMC` — Live Results MDI mutator |
| 107 | LROFIMutator | LROfi | LR#pOFIMutator | MESSAGING | `common/GMC` — Live Results OFI mutator |
| 108 | LRRDSMutator | LRRds | LR#pRDSMutator | MESSAGING | `common/GMC` — Live Results RDS mutator |
| 109 | LRAuthPersistNode | LRAuPe | LR#pAuthPersistNode | MESSAGING | `common/GMC` — Live Results auth/persist node |
| 113 | LRProcessingMutator | LRProMu | LR#pProcessingMutator | MESSAGING | `common/GMC` — Live Results processing mutator |
| 114 | LRCryptoProxy | LRCrPr | LRCryptoProxy | HOCO | `common/GMC` — Live Results crypto proxy |
| 115 | LRGmcGate | LRGmcGt | LR#pGmcGate | MESSAGING | `common/GMC` — GMC gateway node |
| 116 | LRGmcLight | LRGmcLt | LR#pGmcLight | MESSAGING | `common/GMC` — GMC light client node |

---

## Field Reference

| Field | Description |
|-------|-------------|
| `ApplicationTypeID` | Numeric identifier used in CMDB to reference this application type |
| `ShortName` | Abbreviated identifier used in operations tooling and monitoring |
| `ProcessNameTemplate` | Template for the OS process name; `LR#p` prefix = partition-scoped Live Results process |
| `MustBeTierType` | Placement constraint: `Tier` (per-partition server), `Singleton`, `NoTier` (unpartitioned), `JBossTier` (Java/JBoss), `LRTier` (Live Results cluster) |
| `PartitionType` | Partition scoping: `0`=none, `1`=matching partition, `2`=LR partition, `4`=market/product partition, `6`=gateway partition |
| `UsesMessaging` | `1` if the process communicates via the T7 internal messaging bus |
| `UsesRedundancy` | `1` if the process uses file-based redundancy / HA failover |
| `RefDataClientType` | How the process receives reference data: `NONE`, `PRELOADUPDATES_ML` (preload + live updates), `PRELOADSTARTUP_DB` (preload from DB at startup) |
| `MonitoringType` | How the process is monitored: `MESSAGING` (via T7 internal bus), `HOCO` (Host Controller), `SOAP` (SOAP interface) |
| `ApplicationTypeGroup` | `0`=standard, `3`=Live Results (LR), `4`=JBoss/Java services |
