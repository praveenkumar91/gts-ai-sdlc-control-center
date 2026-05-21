
# T7 Component Map

Full component path reference for T7 release `150.001.010`, project=`t7`, env=`eurex`.  
Use these paths as the `component` parameter in `mcp_t7codebase_list_files` and `mcp_t7codebase_search_codebase`.

## Applications (eurex/apps/)

| Component | Description |
|-----------|-------------|
| `eurex/apps/matcher` | Matching Engine |
| `eurex/apps/matcherexternal` | Matcher external interface library |
| `eurex/apps/matchergwval` | Matcher gateway validation |
| `eurex/apps/trade-entry-service` | Trade Entry Service (TES) |
| `eurex/apps/tesgwval` | TES gateway validation |
| `eurex/apps/pate` | Post-Trade (PATE) |
| `eurex/apps/tradecommonutils` | Shared trade utilities |
| `eurex/apps/trademanagergwval` | Trade Manager gateway validation |
| `eurex/apps/tradestatslib` | Trade statistics library |
| `eurex/apps/trade-feed-handler` | Trade Feed Handler (TFH) |
| `eurex/apps/liquidity-discovery-service` | Liquidity Discovery Service (LDS) |
| `eurex/apps/ldsgwval` | LDS gateway validation |
| `eurex/apps/mars` | MARS |
| `eurex/apps/marsgwval` | MARS gateway validation |
| `eurex/apps/bond` | Bond handling |
| `eurex/apps/contractmanager` | Contract Manager |
| `eurex/apps/contractmanager-comm` | Contract Manager communication layer |
| `eurex/apps/contractmanager-xsd` | Contract Manager XSD schemas |
| `eurex/apps/data-distributor-common` | Shared data distributor library |
| `eurex/apps/market-data-obo-incremental` | Order-by-order incremental market data (EOBI) |
| `eurex/apps/market-data-netted` | Netted market data |
| `eurex/apps/market-data-heartbeat` | Market data heartbeat |
| `eurex/apps/market-data-republisher` | Market data republisher |
| `eurex/apps/multicaster` | Multicast distribution |
| `eurex/apps/reference-data-distributor` | Reference Data Distributor (RDD) |
| `eurex/apps/refdata` | Reference data application (GMC-facing) |
| `eurex/apps/refdata-application` | Reference data application framework |
| `eurex/apps/refdata-database` | Reference data DB scripts |
| `eurex/apps/refdata-graphql` | Reference data GraphQL API |
| `eurex/apps/auditfilter` | Audit Trail filter |
| `eurex/apps/fagse` | FAGSE application |
| `eurex/apps/etiasm` | ETI ASM |
| `eurex/apps/newsservice` | News service |
| `eurex/apps/odcserver` | ODC server |
| `eurex/apps/persistence` | Persistence layer |
| `eurex/apps/common` | Shared application utilities |
| `eurex/apps/utility` | Utility tools |
| `eurex/apps/connection-test-gateway` | Connection test gateway |

## Gateways (eurex/gateway/)

| Component | Description |
|-----------|-------------|
| `eurex/gateway/gateway` | ETI Gateway |
| `eurex/gateway/fixgw` | FIX Gateway |
| `eurex/gateway/outboundfi` | Outbound Feed Interface (OFI) |
| `eurex/gateway/odcgw` | ODC Gateway |
| `eurex/gateway/funcvalapi` | Functional Validation API (shared by all gateways) |
| `eurex/gateway/eti` | ETI protocol library |
| `eurex/gateway/edci` | EDCI protocol library |
| `eurex/gateway/edci-docu` | EDCI documentation |
| `eurex/gateway/fix` | FIX protocol library |
| `eurex/gateway/fixdocu` | FIX documentation |
| `eurex/gateway/eurfixdocu` | Eurex FIX documentation |
| `eurex/gateway/outboundfi-docu` | OFI documentation |
| `eurex/gateway/gameinterface` | GAME interface |
| `eurex/gateway/gwconversion` | Gateway conversion utilities |
| `eurex/gateway/fixgwconversion` | FIX gateway conversion utilities |
| `eurex/gateway/fixgw-rule_gen` | FIX gateway rule generator |
| `eurex/gateway/odcgwconversion` | ODC gateway conversion |
| `eurex/gateway/oficonversion` | OFI conversion |
| `eurex/gateway/common` | Shared gateway utilities |

## Data Access (eurex/dataaccess/)

| Component | Description |
|-----------|-------------|
| `eurex/dataaccess/cd-ref` | Central Reference Data Cache config (depends on rdc + view-model) |
| `eurex/dataaccess/rda-outbound-bridge` | RefDataBridge (Eurex-specific outbound bridge) |
| `eurex/dataaccess/rda-common` | Shared RDA utilities |
| `eurex/dataaccess/tradeentryservice` | TES data access layer |
| `eurex/dataaccess/commondb-database` | commondb schema |
| `eurex/dataaccess/commondb-database-conversion` | commondb conversion scripts |
| `eurex/dataaccess/rdb-database` | rdb (reference data) schema |
| `eurex/dataaccess/viewdb-database` | viewdb schema (per marketplace) |
| `eurex/dataaccess/exportdb-database` | exportdb schema |
| `eurex/dataaccess/cross-partition-data` | Cross-partition data structures |
| `eurex/dataaccess/combined-model-plugin` | Combined model plugin |
| `eurex/dataaccess/rdsgen-transformation` | RDS generation transformation |
| `eurex/dataaccess/database-tools` | Database tooling |
| `eurex/dataaccess/mysql-configurations` | MySQL configuration files |
| `eurex/dataaccess/mysql-db-clean-config` | MySQL cleanup config |
| `eurex/dataaccess/mysql-db-users` | MySQL user management |
| `eurex/dataaccess/mysql-scripts` | MySQL scripts |
| `eurex/dataaccess/common` | Shared data access utilities |
| `eurex/specification/view-model` | View model specification |

## Common Data Access (common/dataaccess/)

| Component | Description |
|-----------|-------------|
| `common/dataaccess/rdc` | Reference Data Cache core |
| `common/dataaccess/rda-outbound-bridge-common` | RefDataBridge common (state machine, pool types) |
| `common/dataaccess/rda-inbound-bridge` | Inbound bridge (AMQP → RDS) |
| `common/dataaccess/common` | Shared data access base |
| `common/dataaccess/db-service` | DB service abstraction |
| `common/dataaccess/db-tools` | DB tooling |
| `common/dataaccess/mycxx` | MySQL C++ wrapper |
| `common/dataaccess/mysql-db-clean` | MySQL cleanup base |
| `common/dataaccess/mysql-db-tools` | MySQL DB tools |
| `common/dataaccess/mysql-infodb-database` | Info DB schema |
| `common/dataaccess/mysql-initd` | MySQL init scripts |
| `common/dataaccess/mysql-scripts-common` | Common MySQL scripts |
| `common/dataaccess/sql-service` | SQL service abstraction |
| `common/dataaccess/view-service` | View service |
| `common/dataaccess/viewdb-database-common` | ViewDB common schema |

## Controller-Monitor — Common (common/controller-monitor/)

| Component | Description |
|-----------|-------------|
| `common/controller-monitor/archservice` | Architecture Service Library (BOS/Monitor/Session base) |
| `common/controller-monitor/monitor` | System Monitor |
| `common/controller-monitor/monitorsnmp` | Monitor SNMP interface |
| `common/controller-monitor/monitorsoap` | Monitor SOAP interface |
| `common/controller-monitor/monitorsoapconnector` | Monitor SOAP connector |
| `common/controller-monitor/monitorstatecalc` | Monitor state calculator |
| `common/controller-monitor/bos` | Backend Operations Service (BOS) |
| `common/controller-monitor/autoconversion` | Autoconversion framework base |
| `common/controller-monitor/database` | CMDB management |
| `common/controller-monitor/host` | Host Controller |
| `common/controller-monitor/status` | Status manager |
| `common/controller-monitor/opcon` | Operations console |
| `common/controller-monitor/opmenu` | Operations menu |
| `common/controller-monitor/eventviewer` | Event viewer |
| `common/controller-monitor/gtspythonlibs` | Python helper libraries for operations |

## Controller-Monitor — Eurex-specific (eurex/common/controller-monitor/)

| Component | Description |
|-----------|-------------|
| `eurex/common/controller-monitor/autoconversion` | Eurex autoconversion steps |
| `eurex/common/controller-monitor/bos` | Eurex BOS extensions |
| `eurex/common/controller-monitor/database` | Eurex CMDB extensions |
| `eurex/common/controller-monitor/session` | Session Manager |
| `eurex/common/controller-monitor/opcon` | Eurex operations console |
| `eurex/common/controller-monitor/opmenu` | Eurex operations menu |
| `eurex/common/controller-monitor/monitorsoap` | Eurex monitor SOAP |
| `eurex/common/controller-monitor/monitorsoapconnector` | Eurex monitor SOAP connector |
| `eurex/common/controller-monitor/eventviewer` | Eurex event viewer |
| `eurex/common/controller-monitor/infoscreenadaptor` | Info screen adaptor |

## Messaging (common/ and eurex/)

| Component | Description |
|-----------|-------------|
| `common/messaging` | Core messaging library |
| `common/messaging-jni` | JNI bridge for messaging (GMC/Java) |
| `eurex/messaging` | Eurex-specific messaging extensions |
| `common/amqp` | AMQP base library |
| `common/amqp-qpid` | Qpid AMQP implementation |
| `eurex/cilmsg` | CIL (Clearing Integration Layer) messaging |
| `eurex/intmsg/model/apps` | Application messaging models |
| `eurex/intmsg/model/gateway` | Gateway messaging models |
| `eurex/intmsg/model/matcher` | Matcher messaging models |
| `eurex/intmsg/model/trademanager` | Trade Manager messaging models |
| `eurex/intmsg/model/tradeentryservice` | TES messaging models |
| `eurex/intmsg/model/trade-feed-handler` | TFH messaging models |
| `eurex/intmsg/model/outboundfi` | OFI messaging models |
| `eurex/intmsg/model/fixgw` | FIX GW messaging models |
| `eurex/intmsg/model/liquidity-discovery-service` | LDS messaging models |
| `eurex/intmsg/model/mars` | MARS messaging models |
| `eurex/intmsg/model/referencedata` | Reference data messaging models |
| `eurex/intmsg/model/contractmanager` | Contract Manager messaging models |
| `eurex/intmsg/model/data-distributor-common` | Data distributor messaging models |
| `eurex/intmsg/model/odc` | ODC messaging models |
| `eurex/intmsg/model/bond` | Bond messaging models |
| `eurex/intmsg/model/configspecific` | Config-specific messaging models |
| `eurex/intmsg/model/multicaster` | Multicaster messaging models |

## PerfMon (perfmon/)

| Component | Description |
|-----------|-------------|
| `common/perfmon` | Online Performance Monitor (OPM) — top-level app |
| `perfmon/core` | PerfMon core library |
| `perfmon/capture` | Packet capture module |
| `perfmon/ackstat` | ACK statistics |
| `perfmon/ipasm` | IP ASM module |
| `perfmon/market-data-reader` | Market data reader for PerfMon |
| `perfmon/monsoapproxy` | Monitor SOAP proxy for PerfMon |

## GUI and GMC (common/GMC)

| Component | Description |
|-----------|-------------|
| `common/GMC` | GUI Middleware Cluster (Java, LiveResults) |
| `common/GUI_test_interface` | GUI test interface |
| `common/gmc-packager` | GMC packager |
| `common/webapp` | Web application (GraphQL, REST) |

## Common Services and Utilities (common/service/, common/util/, common/shell)

| Component | Description |
|-----------|-------------|
| `common/shell` | Shell script base library |
| `eurex/common/shell` | Eurex shell script extensions |
| `common/service/logging` | Logging framework |
| `common/service/startup` | Startup scripts base |
| `common/service/scriptbase` | Script base library |
| `common/service/mysql-support` | MySQL support scripts |
| `common/service/mysqlpp-wrapper` | mysqlpp C++ wrapper |
| `common/service/timerlib` | Timer library |
| `common/service/util` | General utilities |
| `common/service/opertools` | Operations tools |
| `common/service/sanity_checks` | Sanity check scripts |
| `common/service/setup` | Environment setup scripts |
| `common/service/system-config` | System configuration |
| `common/service/exception` | Exception handling |
| `common/service/filesystem` | Filesystem utilities |
| `common/service/mlheartbeat` | ML heartbeat service |
| `common/service/activemq-service` | ActiveMQ service wrapper |
| `common/util/atomic` | Atomic utilities |
| `common/util/threadpool` | Thread pool |
| `common/util/fast` | FAST protocol utilities |
| `common/util/cpuaffinitycfg` | CPU affinity configuration |
| `common/util/integtest-conflib` | Integration test config library |
| `common/util/python` | Python utility modules |
| `common/redundancy` | Redundancy/failover library |
| `common/global` | Global constants and definitions |
| `common/releaseinfo` | Release information |

## Eurex Common (eurex/common/)

| Component | Description |
|-----------|-------------|
| `eurex/common/entitlement` | Entitlement library |
| `eurex/common/price-feed-handler` | Price Feed Handler (PFH) |
| `eurex/common/tuned-profiles` | Tuned performance profiles |
| `eurex/conversions` | Conversion utilities |
| `eurex/release` | Release metadata |

## Code Generation Tools (common/tool/, common/efl/, common/flang/)

| Component | Description |
|-----------|-------------|
| `common/tool/fastgen` | FAST message generator |
| `common/tool/immo3` | IMMO3 code generator |
| `common/tool/d2sg3` | D2SG3 tool |
| `common/tool/d2sg_frontend` | D2SG frontend |
| `common/tool/logan3` | Logan3 tool |
| `common/tool/oscar3` | Oscar3 tool |
| `common/efl/generator` | EFL generator |
| `common/flang/generator` | FLang generator |
| `common/refdata/core` | Reference data core generator |
| `common/refdata/generator` | Reference data generator |
| `common/refdata/tool` | Reference data tool |
| `common/message-docu-generator` | Message documentation generator |

## Services and Integration (eurex/service/, eurex/int/)

| Component | Description |
|-----------|-------------|
| `eurex/service/jobschedule` | Job scheduler (JS7) integration |
| `eurex/service/disaster-recovery` | Disaster recovery scripts |
| `eurex/service/opertools` | Eurex operations tools |
| `eurex/service/setup` | Eurex setup scripts |
| `eurex/service/sanity_checks` | Eurex sanity checks |
| `eurex/service/qpid-setup` | Qpid/AMQP broker setup |
| `eurex/int/smoketest` | Smoke tests |
