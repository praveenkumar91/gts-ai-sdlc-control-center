
# T7 Component Map

Full component path reference for T7 release `150.002.010`, project=`t7`, env=`eurex`.  
Use these paths as the `component` parameter in `mcp_codebase-expl_list_files` and `mcp_codebase-expl_search_code`.

## Applications (eurex/apps/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/apps/matcher` | Matching Engine | gts.eurex.apps.matcher |
| `eurex/apps/matcherexternal` | Matcher external interface library | gts.eurex.apps.matcherexternal |
| `eurex/apps/matchergwval` | Matcher gateway validation | gts.eurex.apps.matchergwval |
| `eurex/apps/trade-entry-service` | Trade Entry Service (TES) | gts.eurex.apps.trade-entry-service |
| `eurex/apps/tesgwval` | TES gateway validation | gts.eurex.apps.tesgwval |
| `eurex/apps/pate` | Post-Trade (PATE) | gts.eurex.apps.pate |
| `eurex/apps/tradecommonutils` | Shared trade utilities | gts.eurex.apps.tradecommonutils |
| `eurex/apps/trademanagergwval` | Trade Manager gateway validation | gts.eurex.apps.trademanagergwval |
| `eurex/apps/tradestatslib` | Trade statistics library | gts.eurex.apps.tradestatslib |
| `eurex/apps/trade-feed-handler` | Trade Feed Handler (TFH) | gts.eurex.apps.trade-feed-handler |
| `eurex/apps/liquidity-discovery-service` | Liquidity Discovery Service (LDS) | gts.eurex.apps.liquidity-discovery-service |
| `eurex/apps/ldsgwval` | LDS gateway validation | gts.eurex.apps.ldsgwval |
| `eurex/apps/mars` | MARS | gts.eurex.apps.mars |
| `eurex/apps/marsgwval` | MARS gateway validation | gts.eurex.apps.marsgwval |
| `eurex/apps/bond` | Bond handling | gts.eurex.apps.bond |
| `eurex/apps/contractmanager` | Contract Manager | gts.eurex.apps.contractmanager |
| `eurex/apps/contractmanager-comm` | Contract Manager communication layer | gts.eurex.apps.contractmanager-comm |
| `eurex/apps/contractmanager-xsd` | Contract Manager XSD schemas | gts.eurex.apps.contractmanager-xsd |
| `eurex/apps/data-distributor-common` | Shared data distributor library | gts.eurex.apps.data-distributor-common |
| `eurex/apps/market-data-obo-incremental` | Order-by-order incremental market data (EOBI) | gts.eurex.apps.market-data-obo-incremental |
| `eurex/apps/market-data-netted` | Netted market data | gts.eurex.apps.market-data-netted |
| `eurex/apps/market-data-heartbeat` | Market data heartbeat | gts.eurex.apps.market-data-heartbeat |
| `eurex/apps/market-data-republisher` | Market data republisher | gts.eurex.apps.market-data-republisher |
| `eurex/apps/multicaster` | Multicast distribution | gts.eurex.apps.multicaster |
| `eurex/apps/reference-data-distributor` | Reference Data Distributor (RDD) | gts.eurex.apps.reference-data-distributor |
| `eurex/apps/refdata` | Reference data application (GMC-facing) | gts.eurex.apps.refdata |
| `eurex/apps/refdata-application` | Reference data application framework | gts.eurex.apps.refdata-application |
| `eurex/apps/refdata-database` | Reference data DB scripts | gts.eurex.apps.refdata-database |
| `eurex/apps/refdata-graphql` | Reference data GraphQL API | gts.eurex.apps.refdata-graphql |
| `eurex/apps/auditfilter` | Audit Trail filter | gts.eurex.apps.auditfilter |
| `eurex/apps/fagse` | FAGSE application | gts.eurex.apps.fagse |
| `eurex/apps/etiasm` | ETI ASM | gts.eurex.apps.etiasm |
| `eurex/apps/newsservice` | News service | gts.eurex.apps.newsservice |
| `eurex/apps/odcserver` | ODC server | gts.eurex.apps.odcserver |
| `eurex/apps/persistence` | Persistence layer | gts.eurex.apps.persistence |
| `eurex/apps/common` | Shared application utilities | gts.eurex.apps.common |
| `eurex/apps/utility` | Utility tools | gts.eurex.apps.utility |
| `eurex/apps/connection-test-gateway` | Connection test gateway | gts.eurex.apps.connection-test-gateway |

## Gateways (eurex/gateway/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/gateway/gateway` | ETI Gateway | gts.eurex.gateway.gateway |
| `eurex/gateway/fixgw` | FIX Gateway | gts.eurex.gateway.fixgw |
| `eurex/gateway/outboundfi` | Outbound Feed Interface (OFI) | gts.eurex.gateway.outboundfi |
| `eurex/gateway/odcgw` | ODC Gateway | gts.eurex.gateway.odcgw |
| `eurex/gateway/funcvalapi` | Functional Validation API (shared by all gateways) | gts.eurex.gateway.funcvalapi |
| `eurex/gateway/eti` | ETI protocol library | gts.eurex.gateway.eti |
| `eurex/gateway/edci` | EDCI protocol library | gts.eurex.gateway.edci |
| `eurex/gateway/edci-docu` | EDCI documentation | gts.eurex.gateway.edci-docu |
| `eurex/gateway/fix` | FIX protocol library | gts.eurex.gateway.fix |
| `eurex/gateway/fixdocu` | FIX documentation | gts.eurex.gateway.fixdocu |
| `eurex/gateway/eurfixdocu` | Eurex FIX documentation | gts.eurex.gateway.eurfixdocu |
| `eurex/gateway/outboundfi-docu` | OFI documentation | gts.eurex.gateway.outboundfi-docu |
| `eurex/gateway/gameinterface` | GAME interface | gts.eurex.gateway.gameinterface |
| `eurex/gateway/gwconversion` | Gateway conversion utilities | gts.eurex.gateway.gwconversion |
| `eurex/gateway/fixgwconversion` | FIX gateway conversion utilities | gts.eurex.gateway.fixgwconversion |
| `eurex/gateway/fixgw-rule_gen` | FIX gateway rule generator | gts.eurex.gateway.fixgw-rule_gen |
| `eurex/gateway/odcgwconversion` | ODC gateway conversion | gts.eurex.gateway.odcgwconversion |
| `eurex/gateway/oficonversion` | OFI conversion | gts.eurex.gateway.oficonversion |
| `eurex/gateway/common` | Shared gateway utilities | gts.eurex.gateway.common |

## Data Access (eurex/dataaccess/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/dataaccess/cd-ref` | Central Reference Data Cache config (depends on rdc + view-model) | gts.eurex.dataaccess.cd-ref |
| `eurex/dataaccess/rda-outbound-bridge` | RefDataBridge (Eurex-specific outbound bridge) | gts.eurex.dataaccess.rda-outbound-bridge |
| `eurex/dataaccess/rda-common` | Shared RDA utilities | gts.eurex.dataaccess.rda-common |
| `eurex/dataaccess/tradeentryservice` | TES data access layer | gts.eurex.dataaccess.tradeentryservice |
| `eurex/dataaccess/commondb-database` | commondb schema | gts.eurex.dataaccess.commondb-database |
| `eurex/dataaccess/commondb-database-conversion` | commondb conversion scripts | gts.eurex.dataaccess.commondb-database-conversion |
| `eurex/dataaccess/rdb-database` | rdb (reference data) schema | gts.eurex.dataaccess.rdb-database |
| `eurex/dataaccess/viewdb-database` | viewdb schema (per marketplace) | gts.eurex.dataaccess.viewdb-database |
| `eurex/dataaccess/exportdb-database` | exportdb schema | gts.eurex.dataaccess.exportdb-database |
| `eurex/dataaccess/cross-partition-data` | Cross-partition data structures | gts.eurex.dataaccess.cross-partition-data |
| `eurex/dataaccess/combined-model-plugin` | Combined model plugin | gts.eurex.dataaccess.combined-model-plugin |
| `eurex/dataaccess/rdsgen-transformation` | RDS generation transformation | gts.eurex.dataaccess.rdsgen-transformation |
| `eurex/dataaccess/database-tools` | Database tooling | gts.eurex.dataaccess.database-tools |
| `eurex/dataaccess/mysql-configurations` | MySQL configuration files | gts.eurex.dataaccess.mysql-configurations |
| `eurex/dataaccess/mysql-db-clean-config` | MySQL cleanup config | gts.eurex.dataaccess.mysql-db-clean-config |
| `eurex/dataaccess/mysql-db-users` | MySQL user management | gts.eurex.dataaccess.mysql-db-users |
| `eurex/dataaccess/mysql-scripts` | MySQL scripts | gts.eurex.dataaccess.mysql-scripts |
| `eurex/dataaccess/common` | Shared data access utilities | gts.eurex.dataaccess.common |
| `eurex/specification/view-model` | View model specification | gts.eurex.specification.view-model |

## Common Data Access (common/dataaccess/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/dataaccess/rdc` | Reference Data Cache core | gts.common.dataaccess.rdc |
| `common/dataaccess/rda-outbound-bridge-common` | RefDataBridge common (state machine, pool types) | gts.common.dataaccess.rda-outbound-bridge-common |
| `common/dataaccess/rda-inbound-bridge` | Inbound bridge (AMQP → RDS) | gts.common.dataaccess.rda-inbound-bridge |
| `common/dataaccess/common` | Shared data access base | gts.common.dataaccess.common |
| `common/dataaccess/db-service` | DB service abstraction | gts.common.dataaccess.db-service |
| `common/dataaccess/db-tools` | DB tooling | gts.common.dataaccess.db-tools |
| `common/dataaccess/mycxx` | MySQL C++ wrapper | gts.common.dataaccess.mycxx |
| `common/dataaccess/mysql-db-clean` | MySQL cleanup base | gts.common.dataaccess.mysql-db-clean |
| `common/dataaccess/mysql-db-tools` | MySQL DB tools | gts.common.dataaccess.mysql-db-tools |
| `common/dataaccess/mysql-infodb-database` | Info DB schema | gts.common.dataaccess.mysql-infodb-database |
| `common/dataaccess/mysql-initd` | MySQL init scripts | gts.common.dataaccess.mysql-initd |
| `common/dataaccess/mysql-scripts-common` | Common MySQL scripts | gts.common.dataaccess.mysql-scripts-common |
| `common/dataaccess/sql-service` | SQL service abstraction | gts.common.dataaccess.sql-service |
| `common/dataaccess/view-service` | View service | gts.common.dataaccess.view-service |
| `common/dataaccess/viewdb-database-common` | ViewDB common schema | gts.common.dataaccess.viewdb-database-common |

## Controller-Monitor — Common (common/controller-monitor/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/controller-monitor/archservice` | Architecture Service Library (BOS/Monitor/Session base) | gts.common.controller-monitor.archservice |
| `common/controller-monitor/monitor` | System Monitor | gts.common.controller-monitor.monitor |
| `common/controller-monitor/monitorsnmp` | Monitor SNMP interface | gts.common.controller-monitor.monitorsnmp |
| `common/controller-monitor/monitorsoap` | Monitor SOAP interface | gts.common.controller-monitor.monitorsoap |
| `common/controller-monitor/monitorsoapconnector` | Monitor SOAP connector | gts.common.controller-monitor.monitorsoapconnector |
| `common/controller-monitor/monitorstatecalc` | Monitor state calculator | gts.common.controller-monitor.monitorstatecalc |
| `common/controller-monitor/bos` | Backend Operations Service (BOS) | gts.common.controller-monitor.bos |
| `common/controller-monitor/autoconversion` | Autoconversion framework base | gts.common.controller-monitor.autoconversion |
| `common/controller-monitor/database` | CMDB management | gts.common.controller-monitor.database |
| `common/controller-monitor/host` | Host Controller | gts.common.controller-monitor.host |
| `common/controller-monitor/status` | Status manager | gts.common.controller-monitor.status |
| `common/controller-monitor/opcon` | Operations console | gts.common.controller-monitor.opcon |
| `common/controller-monitor/opmenu` | Operations menu | gts.common.controller-monitor.opmenu |
| `common/controller-monitor/eventviewer` | Event viewer | gts.common.controller-monitor.eventviewer |
| `common/controller-monitor/gtspythonlibs` | Python helper libraries for operations | gts.common.controller-monitor.gtspythonlibs |

## Controller-Monitor — Eurex-specific (eurex/common/controller-monitor/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/common/controller-monitor/autoconversion` | Eurex autoconversion steps | gts.eurex.common.controller-monitor.autoconversion |
| `eurex/common/controller-monitor/bos` | Eurex BOS extensions | gts.eurex.common.controller-monitor.bos |
| `eurex/common/controller-monitor/database` | Eurex CMDB extensions | gts.eurex.common.controller-monitor.database |
| `eurex/common/controller-monitor/session` | Session Manager | gts.eurex.common.controller-monitor.session |
| `eurex/common/controller-monitor/opcon` | Eurex operations console | gts.eurex.common.controller-monitor.opcon |
| `eurex/common/controller-monitor/opmenu` | Eurex operations menu | gts.eurex.common.controller-monitor.opmenu |
| `eurex/common/controller-monitor/monitorsoap` | Eurex monitor SOAP | gts.eurex.common.controller-monitor.monitorsoap |
| `eurex/common/controller-monitor/monitorsoapconnector` | Eurex monitor SOAP connector | gts.eurex.common.controller-monitor.monitorsoapconnector |
| `eurex/common/controller-monitor/eventviewer` | Eurex event viewer | gts.eurex.common.controller-monitor.eventviewer |
| `eurex/common/controller-monitor/infoscreenadaptor` | Info screen adaptor | gts.eurex.common.controller-monitor.infoscreenadaptor |

## Messaging (common/ and eurex/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/messaging` | Core messaging library | gts.common.messaging |
| `common/messaging-jni` | JNI bridge for messaging (GMC/Java) | gts.common.messaging-jni |
| `eurex/messaging` | Eurex-specific messaging extensions | gts.eurex.messaging |
| `common/amqp` | AMQP base library | gts.common.amqp |
| `common/amqp-qpid` | Qpid AMQP implementation | gts.common.amqp-qpid |
| `eurex/cilmsg` | CIL (Clearing Integration Layer) messaging | gts.eurex.cilmsg |
| `eurex/intmsg/model/apps` | Application messaging models | gts.eurex.intmsg.model.apps |
| `eurex/intmsg/model/gateway` | Gateway messaging models | gts.eurex.intmsg.model.gateway |
| `eurex/intmsg/model/matcher` | Matcher messaging models | gts.eurex.intmsg.model.matcher |
| `eurex/intmsg/model/trademanager` | Trade Manager messaging models | gts.eurex.intmsg.model.trademanager |
| `eurex/intmsg/model/tradeentryservice` | TES messaging models | gts.eurex.intmsg.model.tradeentryservice |
| `eurex/intmsg/model/trade-feed-handler` | TFH messaging models | gts.eurex.intmsg.model.trade-feed-handler |
| `eurex/intmsg/model/outboundfi` | OFI messaging models | gts.eurex.intmsg.model.outboundfi |
| `eurex/intmsg/model/fixgw` | FIX GW messaging models | gts.eurex.intmsg.model.fixgw |
| `eurex/intmsg/model/liquidity-discovery-service` | LDS messaging models | gts.eurex.intmsg.model.liquidity-discovery-service |
| `eurex/intmsg/model/mars` | MARS messaging models | gts.eurex.intmsg.model.mars |
| `eurex/intmsg/model/referencedata` | Reference data messaging models | gts.eurex.intmsg.model.referencedata |
| `eurex/intmsg/model/contractmanager` | Contract Manager messaging models | gts.eurex.intmsg.model.contractmanager |
| `eurex/intmsg/model/data-distributor-common` | Data distributor messaging models | gts.eurex.intmsg.model.data-distributor-common |
| `eurex/intmsg/model/odc` | ODC messaging models | gts.eurex.intmsg.model.odc |
| `eurex/intmsg/model/bond` | Bond messaging models | gts.eurex.intmsg.model.bond |
| `eurex/intmsg/model/configspecific` | Config-specific messaging models | gts.eurex.intmsg.model.configspecific |
| `eurex/intmsg/model/multicaster` | Multicaster messaging models | gts.eurex.intmsg.model.multicaster |

## PerfMon (perfmon/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/perfmon` | Online Performance Monitor (OPM) — top-level app | gts.common.perfmon |
| `perfmon/core` | PerfMon core library | gts.perfmon.core |
| `perfmon/capture` | Packet capture module | gts.perfmon.capture |
| `perfmon/ackstat` | ACK statistics | gts.perfmon.ackstat |
| `perfmon/ipasm` | IP ASM module | gts.perfmon.ipasm |
| `perfmon/market-data-reader` | Market data reader for PerfMon | gts.perfmon.market-data-reader |
| `perfmon/monsoapproxy` | Monitor SOAP proxy for PerfMon | gts.perfmon.monsoapproxy |

## GUI and GMC (common/GMC)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/GMC` | GUI Middleware Cluster (Java, LiveResults) | gts.common.GMC |
| `common/GUI_test_interface` | GUI test interface | gts.common.GUI_test_interface |
| `common/gmc-packager` | GMC packager | gts.common.gmc-packager |
| `common/webapp` | Web application (GraphQL, REST) | gts.common.webapp |

## Common Services and Utilities (common/service/, common/util/, common/shell)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/shell` | Shell script base library | gts.common.shell |
| `eurex/common/shell` | Eurex shell script extensions | gts.eurex.common.shell |
| `common/service/logging` | Logging framework | gts.common.service.logging |
| `common/service/startup` | Startup scripts base | gts.common.service.startup |
| `common/service/scriptbase` | Script base library | gts.common.service.scriptbase |
| `common/service/mysql-support` | MySQL support scripts | gts.common.service.mysql-support |
| `common/service/mysqlpp-wrapper` | mysqlpp C++ wrapper | gts.common.service.mysqlpp-wrapper |
| `common/service/timerlib` | Timer library | gts.common.service.timerlib |
| `common/service/util` | General utilities | gts.common.service.util |
| `common/service/opertools` | Operations tools | gts.common.service.opertools |
| `common/service/sanity_checks` | Sanity check scripts | gts.common.service.sanity_checks |
| `common/service/setup` | Environment setup scripts | gts.common.service.setup |
| `common/service/system-config` | System configuration | gts.common.service.system-config |
| `common/service/exception` | Exception handling | gts.common.service.exception |
| `common/service/filesystem` | Filesystem utilities | gts.common.service.filesystem |
| `common/service/mlheartbeat` | ML heartbeat service | gts.common.service.mlheartbeat |
| `common/service/activemq-service` | ActiveMQ service wrapper | gts.common.service.activemq-service |
| `common/util/atomic` | Atomic utilities | gts.common.util.atomic |
| `common/util/threadpool` | Thread pool | gts.common.util.threadpool |
| `common/util/fast` | FAST protocol utilities | gts.common.util.fast |
| `common/util/cpuaffinitycfg` | CPU affinity configuration | gts.common.util.cpuaffinitycfg |
| `common/util/integtest-conflib` | Integration test config library | gts.common.util.integtest-conflib |
| `common/util/python` | Python utility modules | gts.common.util.python |
| `common/redundancy` | Redundancy/failover library | gts.common.redundancy |
| `common/global` | Global constants and definitions | gts.common.global |
| `common/releaseinfo` | Release information | gts.common.releaseinfo |

## Eurex Common (eurex/common/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/common/entitlement` | Entitlement library | gts.eurex.common.entitlement |
| `eurex/common/price-feed-handler` | Price Feed Handler (PFH) | gts.eurex.common.price-feed-handler |
| `eurex/common/tuned-profiles` | Tuned performance profiles | gts.eurex.common.tuned-profiles |
| `eurex/conversions` | Conversion utilities | gts.eurex.conversions |
| `eurex/release` | Release metadata | gts.eurex.release |

## Code Generation Tools (common/tool/, common/efl/, common/flang/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `common/tool/fastgen` | FAST message generator | gts.common.tool.fastgen |
| `common/tool/immo3` | IMMO3 code generator | gts.common.tool.immo3 |
| `common/tool/d2sg3` | D2SG3 tool | gts.common.tool.d2sg3 |
| `common/tool/d2sg_frontend` | D2SG frontend | gts.common.tool.d2sg_frontend |
| `common/tool/logan3` | Logan3 tool | gts.common.tool.logan3 |
| `common/tool/oscar3` | Oscar3 tool | gts.common.tool.oscar3 |
| `common/efl/generator` | EFL generator | gts.common.efl.generator |
| `common/flang/generator` | FLang generator | gts.common.flang.generator |
| `common/refdata/core` | Reference data core generator | gts.common.refdata.core |
| `common/refdata/generator` | Reference data generator | gts.common.refdata.generator |
| `common/refdata/tool` | Reference data tool | gts.common.refdata.tool |
| `common/message-docu-generator` | Message documentation generator | gts.common.message-docu-generator |

## Services and Integration (eurex/service/, eurex/int/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `eurex/service/jobschedule` | Job scheduler (JS7) integration | gts.eurex.service.jobschedule |
| `eurex/service/disaster-recovery` | Disaster recovery scripts | gts.eurex.service.disaster-recovery |
| `eurex/service/opertools` | Eurex operations tools | gts.eurex.service.opertools |
| `eurex/service/setup` | Eurex setup scripts | gts.eurex.service.setup |
| `eurex/service/sanity_checks` | Eurex sanity checks | gts.eurex.service.sanity_checks |
| `eurex/service/qpid-setup` | Qpid/AMQP broker setup | gts.eurex.service.qpid-setup |
| `eurex/int/smoketest` | Smoke tests | gts.eurex.int.smoketest |

## Third-Party Libraries (thirdparty/)

| Component | Description | Repository |
|-----------|-------------|------------|
| `thirdparty/activemq-cpp-library` | Apache ActiveMQ C++ client library — JMS messaging | gts.thirdparty.activemq-cpp-library |
| `thirdparty/amq-broker` | Apache ActiveMQ Artemis — message broker | gts.thirdparty.amq-broker |
| `thirdparty/ansible` | Ansible — IT automation and configuration management | gts.thirdparty.ansible |
| `thirdparty/apache-arrow` | Apache Arrow — in-memory columnar analytics format | gts.thirdparty.apache-arrow |
| `thirdparty/apache-tomcat` | Apache Tomcat — Java servlet container | gts.thirdparty.apache-tomcat |
| `thirdparty/boost` | Boost C++ Libraries — general-purpose C++ utilities | gts.thirdparty.boost |
| `thirdparty/catch2` | Catch2 — modern C++ unit test framework | gts.thirdparty.catch2 |
| `thirdparty/cllm` | CLLM — low-latency messaging library | gts.thirdparty.cllm |
| `thirdparty/copy/org/eclipse` | Eclipse Java framework components (redistribution copy) | gts.thirdparty.copy.org.eclipse |
| `thirdparty/cpython` | CPython — Python interpreter runtime | gts.thirdparty.cpython |
| `thirdparty/cyberark` | CyberArk — privileged access management (PAM) SDK | gts.thirdparty.cyberark |
| `thirdparty/d3` | D3.js — data visualization JavaScript library | gts.thirdparty.d3 |
| `thirdparty/enterpriseonload` | Solarflare/AMD EnterpriseOnload — kernel-bypass networking | gts.thirdparty.enterpriseonload |
| `thirdparty/flot` | Flot — jQuery-based JavaScript charting library | gts.thirdparty.flot |
| `thirdparty/getdown` | Getdown — Java application deployment and auto-update framework | gts.thirdparty.getdown |
| `thirdparty/googletest` | Google Test (GTest/GMock) — C++ testing framework | gts.thirdparty.googletest |
| `thirdparty/gperftools` | Google Performance Tools — tcmalloc, heap profiler, CPU profiler | gts.thirdparty.gperftools |
| `thirdparty/gsoap` | gSOAP — C/C++ SOAP web services toolkit | gts.thirdparty.gsoap |
| `thirdparty/jboss-amqp-connector` | Red Hat JBoss AMQP JMS connector for WildFly | gts.thirdparty.jboss-amqp-connector |
| `thirdparty/jboss-generic-jms-ra` | JBoss Generic JMS Resource Adapter for WildFly | gts.thirdparty.jboss-generic-jms-ra |
| `thirdparty/jboss-mysql-connector` | MySQL JDBC connector for JBoss/WildFly | gts.thirdparty.jboss-mysql-connector |
| `thirdparty/jboss-wildfly` | WildFly (JBoss) — Java EE application server | gts.thirdparty.jboss-wildfly |
| `thirdparty/jide` | JIDE Swing Component Suite — Java GUI widget library | gts.thirdparty.jide |
| `thirdparty/jquery` | jQuery — JavaScript DOM/AJAX library | gts.thirdparty.jquery |
| `thirdparty/jquery-svg` | jQuery SVG — jQuery plugin for SVG rendering | gts.thirdparty.jquery-svg |
| `thirdparty/jquery-ui` | jQuery UI — interaction and widget library | gts.thirdparty.jquery-ui |
| `thirdparty/js7` | JS7 JobScheduler — workflow and job scheduling engine | gts.thirdparty.js7 |
| `thirdparty/latex` | LaTeX — document preparation system | gts.thirdparty.latex |
| `thirdparty/libreoffice` | LibreOffice — office productivity suite | gts.thirdparty.libreoffice |
| `thirdparty/libunwind` | libunwind — portable stack-frame unwinding library | gts.thirdparty.libunwind |
| `thirdparty/mydumper` | mydumper/myloader — fast MySQL logical backup tool | gts.thirdparty.mydumper |
| `thirdparty/mysql-advanced` | Oracle MySQL Advanced/Enterprise server | gts.thirdparty.mysql-advanced |
| `thirdparty/mysql-enterprise-backup` | Oracle MySQL Enterprise Backup | gts.thirdparty.mysql-enterprise-backup |
| `thirdparty/mysqlpp` | MySQL++ — C++ wrapper for the MySQL C API | gts.thirdparty.mysqlpp |
| `thirdparty/nats-c` | cnats — NATS C client library | gts.thirdparty.nats-c |
| `thirdparty/nats-cli` | NATS CLI — command-line tool for NATS | gts.thirdparty.nats-cli |
| `thirdparty/nats-server` | NATS — publish-subscribe messaging server | gts.thirdparty.nats-server |
| `thirdparty/nustaq/fast-serialization` | Nustaq FST — fast Java serialization library | gts.thirdparty.nustaq.fast-serialization |
| `thirdparty/nustaq/kontraktor` | Nustaq Kontraktor — Java actor-based reactive programming | gts.thirdparty.nustaq.kontraktor |
| `thirdparty/opentelemetry-cpp` | OpenTelemetry C++ SDK — distributed tracing/observability | gts.thirdparty.opentelemetry-cpp |
| `thirdparty/pcapplusplus` | PcapPlusPlus — C++ network packet capture and processing | gts.thirdparty.pcapplusplus |
| `thirdparty/pq` | libpq — PostgreSQL C client library | gts.thirdparty.pq |
| `thirdparty/prometheus` | Prometheus — metrics monitoring and alerting system | gts.thirdparty.prometheus |
| `thirdparty/prometheus-nats-exporter` | Prometheus metrics exporter for NATS | gts.thirdparty.prometheus-nats-exporter |
| `thirdparty/protobuf` | Protocol Buffers (C++) — Google's binary serialization | gts.thirdparty.protobuf |
| `thirdparty/protobuf-python3` | Protocol Buffers — Python 3 bindings | gts.thirdparty.protobuf-python3 |
| `thirdparty/pybind11` | pybind11 — seamless C++/Python binding library | gts.thirdparty.pybind11 |
| `thirdparty/pygobject` | PyGObject — Python bindings for GObject/GLib | gts.thirdparty.pygobject |
| `thirdparty/pypam` | python-pam — Python PAM authentication bindings | gts.thirdparty.pypam |
| `thirdparty/python-autobahn` | Autobahn — Python WebSocket and WAMP protocol library | gts.thirdparty.python-autobahn |
| `thirdparty/python-mysql-connector` | MySQL Connector/Python | gts.thirdparty.python-mysql-connector |
| `thirdparty/python-pyxb` | PyXB — Python XML Schema to Python binding compiler | gts.thirdparty.python-pyxb |
| `thirdparty/python-sqlalchemy` | SQLAlchemy — Python SQL toolkit and ORM | gts.thirdparty.python-sqlalchemy |
| `thirdparty/python-sqlsoup` | SQLSoup — reflection-based Python DB access layer | gts.thirdparty.python-sqlsoup |
| `thirdparty/python-twisted` | Twisted — Python event-driven networking framework | gts.thirdparty.python-twisted |
| `thirdparty/python-txaio` | txaio — asyncio/Twisted compatibility layer for Python | gts.thirdparty.python-txaio |
| `thirdparty/python-urwid` | Urwid — Python console user-interface library | gts.thirdparty.python-urwid |
| `thirdparty/python-zope-testrunner` | Zope testrunner — Python test discovery and runner | gts.thirdparty.python-zope-testrunner |
| `thirdparty/python3-zsi` | ZSI — Zolera SOAP Infrastructure Python 3 SOAP library | gts.thirdparty.python3-zsi |
| `thirdparty/qpid-cpp` | Apache Qpid C++ — AMQP message broker/client libraries | gts.thirdparty.qpid-cpp |
| `thirdparty/qpid-proton` | Apache Qpid Proton — AMQP 1.0 messaging library | gts.thirdparty.qpid-proton |
| `thirdparty/quickfix` | QuickFIX — C++ FIX protocol engine | gts.thirdparty.quickfix |
| `thirdparty/rsyslog` | rsyslog — enhanced syslog daemon | gts.thirdparty.rsyslog |
| `thirdparty/s5cmd` | s5cmd — parallel S3/object-storage command-line tool | gts.thirdparty.s5cmd |
| `thirdparty/stomppy` | stomp.py — Python STOMP messaging protocol client | gts.thirdparty.stomppy |
| `thirdparty/xsd` | CodeSynthesis XSD — C++ XML Schema to C++ code compiler | gts.thirdparty.xsd |
