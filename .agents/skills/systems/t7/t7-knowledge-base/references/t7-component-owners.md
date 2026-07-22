# T7 Component Ownership

> Source: `SELECT * FROM CMDB.ComponentOwnership ORDER BY Repository` — queried 2026-05-20.
> Enhanced: 2026-05-28 — added missing MARS and market-data-republisher entries; corrected duplicate `(U) (U)` department labels.
>
> **Department legend:**
> - `AD Trading Core (U)` — Application Development, Trading Core (Matching Engine, PATE, market data)
> - `AD Interface Design & Gateways (U)` — Application Development, Interface Design & Gateways (ETI, FIX, OFI, ODC, MARS)
> - `AD Trading Prague (U)` — Application Development, Trading Prague (TES, trade utilities)
> - `AD Trading Architecture (U)` — Application Development, Trading Architecture (infrastructure, controller-monitor, data access)
> - `AD Trading RDS (U)` — Application Development, Trading Reference Data Systems
> - `AD OPM & Cloud Simulation (U)` — Application Development, Online Performance Monitor & Cloud Simulation
> - `AD Trading GUI (U)` — Application Development, Trading GUI (GMC, Live Results)
> - `Integr.,Configur.Mgmt&Dev.OpsTool (U)` — Integration, Configuration Management & DevOps Tools
> - `Trading System Analytics (U)` — Trading System Analytics (packet capture, performance tooling)
> - `Mainframe Application Development (U)` — Mainframe Application Development (FAGSE legacy gateway)
> - `Calibration & Analytics Services (U)` — Calibration & Analytics Services (AMQP messaging)
> - `Xetra/Eurex Operations (Dpt)` — Xetra/Eurex Operations Department

---

| REPOSITORY | COMPONENT | DEPARTMENT |
| --- | --- | --- |
| build | gts.build | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/amqp | gts.common.amqp | Calibration & Analytics Services (U) |
| common/amqp-qpid | gts.common.amqp-qpid | Calibration & Analytics Services (U) |
| common/build/bfw2mvn | gts.common.build.bfw2mvn | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/build/constants | gts.common.build.constants | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/build/pom | gts.common.build.pom | AD Trading Architecture (U) |
| common/build/stp | gts.common.build.stp | AD Trading Architecture (U) |
| common/build/stream | gts.common.build.stream | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/controller-monitor/archservice | gts.common.controller-monitor.archservice | AD Trading Architecture (U) |
| common/controller-monitor/autoconversion | gts.common.controller-monitor.autoconversion | AD Trading Architecture (U) |
| common/controller-monitor/bos | gts.common.controller-monitor.bos | AD Trading Architecture (U) |
| common/controller-monitor/database | gts.common.controller-monitor.database | AD Trading Architecture (U) |
| common/controller-monitor/eventviewer | gts.common.controller-monitor.eventviewer | AD Trading Architecture (U) |
| common/controller-monitor/gtspythonlibs | gts.common.controller-monitor.gtspythonlibs | AD Trading Architecture (U) |
| common/controller-monitor/host | gts.common.controller-monitor.host | AD Trading Architecture (U) |
| common/controller-monitor/monitor | gts.common.controller-monitor.monitor | AD Trading Architecture (U) |
| common/controller-monitor/monitorsnmp | gts.common.controller-monitor.monitorsnmp | AD Trading Architecture (U) |
| common/controller-monitor/monitorsoap | gts.common.controller-monitor.monitorsoap | AD Trading Architecture (U) |
| common/controller-monitor/monitorsoapconnector | gts.common.controller-monitor.monitorsoapconnector | AD Trading Architecture (U) |
| common/controller-monitor/monitorstatecalc | gts.common.controller-monitor.monitorstatecalc | AD Trading Architecture (U) |
| common/controller-monitor/opcon | gts.common.controller-monitor.opcon | AD Trading Architecture (U) |
| common/controller-monitor/opmenu | gts.common.controller-monitor.opmenu | AD Trading Architecture (U) |
| common/controller-monitor/status | gts.common.controller-monitor.status | AD Trading Architecture (U) |
| common/dataaccess/common | gts.common.dataaccess.common | AD Trading Architecture (U) |
| common/dataaccess/db-service | gts.common.dataaccess.db-service | AD Trading Architecture (U) |
| common/dataaccess/db-tools | gts.common.dataaccess.db-tools | AD Trading Architecture (U) |
| common/dataaccess/mycxx | gts.common.dataaccess.mycxx | AD Trading Architecture (U) |
| common/dataaccess/mysql-db-clean | gts.common.dataaccess.mysql-db-clean | AD Trading Architecture (U) |
| common/dataaccess/mysql-db-tools | gts.common.dataaccess.mysql-db-tools | AD Trading Architecture (U) |
| common/dataaccess/mysql-infodb-database | gts.common.dataaccess.mysql-infodb-database | AD Trading Architecture (U) |
| common/dataaccess/mysql-initd | gts.common.dataaccess.mysql-initd | AD Trading Architecture (U) |
| common/dataaccess/mysql-scripts-common | gts.common.dataaccess.mysql-scripts-common | AD Trading Architecture (U) |
| common/dataaccess/rda-inbound-bridge | gts.common.dataaccess.rda-inbound-bridge | AD Trading Architecture (U) |
| common/dataaccess/rda-outbound-bridge-common | gts.common.dataaccess.rda-outbound-bridge-common | AD Trading Architecture (U) |
| common/dataaccess/rdc | gts.common.dataaccess.rdc | AD Trading Architecture (U) |
| common/dataaccess/sql-service | gts.common.dataaccess.sql-service | AD Trading Architecture (U) |
| common/dataaccess/view-service | gts.common.dataaccess.view-service | AD Trading Architecture (U) |
| common/dataaccess/viewdb-database-common | gts.common.dataaccess.viewdb-database-common | AD Trading Architecture (U) |
| common/efl/generator | gts.common.efl.generator | AD Trading Architecture (U) |
| common/flang/generator | gts.common.flang.generator | AD Trading Architecture (U) |
| common/flang/test | gts.common.flang.test | AD Trading Architecture (U) |
| common/global | gts.common.global | AD Trading Architecture (U) |
| common/GMC | gts.common.GMC | AD Trading GUI (U) |
| common/gmc-packager | gts.common.gmc-packager | Xetra/Eurex Operations (Dpt) |
| common/GUI_test_interface | gts.common.GUI_test_interface | AD Trading GUI (U) |
| common/int/dnf-deployer | gts.common.int.dnf-deployer | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/int/requirements | gts.common.int.requirements | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/intmsg/check | gts.common.intmsg.check | AD Trading Architecture (U) |
| common/intmsg/generator | gts.common.intmsg.generator | AD Trading Architecture (U) |
| common/intmsg/lib | gts.common.intmsg.lib | AD Trading Architecture (U) |
| common/intmsg/model/common | gts.common.intmsg.model.common | AD Trading Architecture (U) |
| common/intmsg/model/config | gts.common.intmsg.model.config | AD Trading Architecture (U) |
| common/intmsg/model/dataaccess | gts.common.intmsg.model.dataaccess | AD Trading Architecture (U) |
| common/intmsg/model/gatewaycommon | gts.common.intmsg.model.gatewaycommon | AD Trading Architecture (U) |
| common/intmsg/model/messaging | gts.common.intmsg.model.messaging | AD Trading Architecture (U) |
| common/intmsg/model/perfmon | gts.common.intmsg.model.perfmon | AD OPM & Cloud Simulation (U) |
| common/intmsg/model/playground | gts.common.intmsg.model.playground | AD Trading Architecture (U) |
| common/message-docu-generator | gts.common.message-docu-generator | AD Trading Architecture (U) |
| common/messaging | gts.common.messaging | AD Trading Architecture (U) |
| common/messaging-jni | gts.common.messaging-jni | AD Trading Architecture (U) |
| common/perfmon | gts.common.perfmon | AD OPM & Cloud Simulation (U) |
| common/redundancy | gts.common.redundancy | AD Trading Architecture (U) |
| common/refdata/core | gts.common.refdata.core | AD Trading RDS (U) |
| common/refdata/generator | gts.common.refdata.generator | AD Trading RDS (U) |
| common/refdata/tool | gts.common.refdata.tool | AD Trading RDS (U) |
| common/releaseinfo | gts.common.releaseinfo | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/service/activemq-service | gts.common.service.activemq-service | AD Trading Architecture (U) |
| common/service/environment | gts.common.service.environment | AD Trading Architecture (U) |
| common/service/exception | gts.common.service.exception | AD Trading Architecture (U) |
| common/service/filesystem | gts.common.service.filesystem | AD Trading Architecture (U) |
| common/service/logging | gts.common.service.logging | AD Trading Architecture (U) |
| common/service/mlheartbeat | gts.common.service.mlheartbeat | AD Trading Architecture (U) |
| common/service/mysql-model-converter | gts.common.service.mysql-model-converter | AD Trading Architecture (U) |
| common/service/mysql-support | gts.common.service.mysql-support | AD Trading Architecture (U) |
| common/service/mysqlpp-wrapper | gts.common.service.mysqlpp-wrapper | AD Trading Architecture (U) |
| common/service/opertools | gts.common.service.opertools | AD Trading Architecture (U) |
| common/service/sanity_checks | gts.common.service.sanity_checks | AD Trading Architecture (U) |
| common/service/scriptbase | gts.common.service.scriptbase | AD Trading Architecture (U) |
| common/service/setup | gts.common.service.setup | AD Trading Architecture (U) |
| common/service/startup | gts.common.service.startup | AD Trading Architecture (U) |
| common/service/system-accounts | gts.common.service.system-accounts | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/service/system-config | gts.common.service.system-config | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/service/system-config-env | gts.common.service.system-config-env | AD Trading Architecture (U) |
| common/service/system-config-yum | gts.common.service.system-config-yum | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/service/timerlib | gts.common.service.timerlib | AD Trading Architecture (U) |
| common/service/util | gts.common.service.util | AD Trading Architecture (U) |
| common/shell | gts.common.shell | AD Trading Architecture (U) |
| common/tool/d2sg3 | gts.common.tool.d2sg3 | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/tool/d2sg_frontend | gts.common.tool.d2sg_frontend | AD Trading Prague (U) |
| common/tool/fastgen | gts.common.tool.fastgen | AD Trading Architecture (U) |
| common/tool/grobi/eurex/elisting-model | gts.common.tool.grobi.eurex.elisting-model | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/tool/grobi/xml-report-model | gts.common.tool.grobi.xml-report-model | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/tool/immo3 | gts.common.tool.immo3 | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/tool/logan3 | gts.common.tool.logan3 | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/tool/oscar3 | gts.common.tool.oscar3 | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/util/amq-broker | gts.common.util.amq-broker | AD Trading Architecture (U) |
| common/util/asan | gts.common.util.asan | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/util/atomic | gts.common.util.atomic | AD Trading Architecture (U) |
| common/util/cpuaffinitycfg | gts.common.util.cpuaffinitycfg | AD Trading Architecture (U) |
| common/util/fast | gts.common.util.fast | AD Trading Core (U) |
| common/util/integtest-conflib | gts.common.util.integtest-conflib | AD Trading Architecture (U) |
| common/util/jboss | gts.common.util.jboss | AD Trading Architecture (U) |
| common/util/jre | gts.common.util.jre | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/util/oaw | gts.common.util.oaw | AD Trading Architecture (U) |
| common/util/onloadutil | gts.common.util.onloadutil | AD Trading Core (U) |
| common/util/python | gts.common.util.python | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| common/util/threadpool | gts.common.util.threadpool | AD Trading Core (U) |
| common/webapp | gts.common.webapp | AD Trading GUI (U) |
| eurex/apps/auditfilter | gts.eurex.apps.auditfilter | AD Trading Core (U) |
| eurex/apps/bond | gts.eurex.apps.bond | AD Trading Architecture (U) |
| eurex/apps/common | gts.eurex.apps.common | AD Trading Core (U) |
| eurex/apps/connection-test-gateway | gts.eurex.apps.connection-test-gateway | AD Trading Architecture (U) |
| eurex/apps/contractmanager | gts.eurex.apps.contractmanager | AD Trading Architecture (U) |
| eurex/apps/contractmanager-comm | gts.eurex.apps.contractmanager-comm | AD Trading Architecture (U) |
| eurex/apps/contractmanager-xsd | gts.eurex.apps.contractmanager-xsd | AD Trading Architecture (U) |
| eurex/apps/data-distributor-common | gts.eurex.apps.data-distributor-common | AD Trading Core (U) |
| eurex/apps/etiasm | gts.eurex.apps.etiasm | AD OPM & Cloud Simulation (U) |
| eurex/apps/fagse | gts.eurex.apps.fagse | Mainframe Application Development (U) |
| eurex/apps/ldsgwval | gts.eurex.apps.ldsgwval | AD Interface Design & Gateways (U) |
| eurex/apps/liquidity-discovery-service | gts.eurex.apps.liquidity-discovery-service | AD Interface Design & Gateways (U) |
| eurex/apps/market-data-heartbeat | gts.eurex.apps.market-data-heartbeat | AD Trading Core (U) |
| eurex/apps/market-data-netted | gts.eurex.apps.market-data-netted | AD Trading Core (U) |
| eurex/apps/market-data-obo-incremental | gts.eurex.apps.market-data-obo-incremental | AD Trading Core (U) |
| eurex/apps/market-data-republisher | gts.eurex.apps.market-data-republisher | AD Trading Core (U) |
| eurex/apps/mars | gts.eurex.apps.mars | AD Interface Design & Gateways (U) |
| eurex/apps/marsgwval | gts.eurex.apps.marsgwval | AD Interface Design & Gateways (U) |
| eurex/apps/matcher | gts.eurex.apps.matcher | AD Trading Core (U) |
| eurex/apps/matcherexternal | gts.eurex.apps.matcherexternal | AD Trading Core (U) |
| eurex/apps/matchergwval | gts.eurex.apps.matchergwval | AD Trading Core (U) |
| eurex/apps/multicaster | gts.eurex.apps.multicaster | AD Trading Core (U) |
| eurex/apps/newsservice | gts.eurex.apps.newsservice | AD Trading Core (U) |
| eurex/apps/odcserver | gts.eurex.apps.odcserver | AD Interface Design & Gateways (U) |
| eurex/apps/pate | gts.eurex.apps.pate | AD Trading Core (U) |
| eurex/apps/persistence | gts.eurex.apps.persistence | AD Trading Core (U) |
| eurex/apps/refdata | gts.eurex.apps.refdata | AD Trading RDS (U) |
| eurex/apps/refdata-application | gts.eurex.apps.refdata-application | AD Trading RDS (U) |
| eurex/apps/refdata-database | gts.eurex.apps.refdata-database | AD Trading RDS (U) |
| eurex/apps/refdata-graphql | gts.eurex.apps.refdata-graphql | AD Trading RDS (U) |
| eurex/apps/reference-data-distributor | gts.eurex.apps.reference-data-distributor | AD Trading Core (U) |
| eurex/apps/tesgwval | gts.eurex.apps.tesgwval | AD Trading Prague (U) |
| eurex/apps/test/tools/auditstream | gts.eurex.apps.test.tools.auditstream | AD Trading Core (U) |
| eurex/apps/trade-entry-service | gts.eurex.apps.trade-entry-service | AD Trading Prague (U) |
| eurex/apps/trade-feed-handler | gts.eurex.apps.trade-feed-handler | AD Interface Design & Gateways (U) |
| eurex/apps/tradecommonutils | gts.eurex.apps.tradecommonutils | AD Trading Prague (U) |
| eurex/apps/trademanagergwval | gts.eurex.apps.trademanagergwval | AD Trading Core (U) |
| eurex/apps/tradestatslib | gts.eurex.apps.tradestatslib | AD Trading Core (U) |
| eurex/apps/utility | gts.eurex.apps.utility | AD Trading Core (U) |
| eurex/cilmsg | gts.eurex.cilmsg | AD Trading Architecture (U) |
| eurex/common/controller-monitor/autoconversion | gts.eurex.common.controller-monitor.autoconversion | AD Trading Architecture (U) |
| eurex/common/controller-monitor/bos | gts.eurex.common.controller-monitor.bos | AD Trading Architecture (U) |
| eurex/common/controller-monitor/database | gts.eurex.common.controller-monitor.database | AD Trading Architecture (U) |
| eurex/common/controller-monitor/eventviewer | gts.eurex.common.controller-monitor.eventviewer | AD Trading Architecture (U) |
| eurex/common/controller-monitor/infoscreenadaptor | gts.eurex.common.controller-monitor.infoscreenadaptor | AD Trading Architecture (U) |
| eurex/common/controller-monitor/monitorsoap | gts.eurex.common.controller-monitor.monitorsoap | AD Trading Architecture (U) |
| eurex/common/controller-monitor/monitorsoapconnector | gts.eurex.common.controller-monitor.monitorsoapconnector | AD Trading Architecture (U) |
| eurex/common/controller-monitor/opcon | gts.eurex.common.controller-monitor.opcon | AD Trading Architecture (U) |
| eurex/common/controller-monitor/opmenu | gts.eurex.common.controller-monitor.opmenu | AD Trading Architecture (U) |
| eurex/common/controller-monitor/session | gts.eurex.common.controller-monitor.session | AD Trading Architecture (U) |
| eurex/common/entitlement | gts.eurex.common.entitlement | AD Trading Core (U) |
| eurex/common/price-feed-handler | gts.eurex.common.price-feed-handler | AD Trading Architecture (U) |
| eurex/common/shell | gts.eurex.common.shell | AD Trading Architecture (U) |
| eurex/common/tuned-profiles | gts.eurex.common.tuned-profiles | Trading System Analytics (U) |
| eurex/conversions | gts.eurex.conversions | Xetra/Eurex Clearing Applications Administration (U) |
| eurex/dataaccess/cd-ref | gts.eurex.dataaccess.cd-ref | AD Trading Architecture (U) |
| eurex/dataaccess/combined-model-plugin | gts.eurex.dataaccess.combined-model-plugin | AD Trading Architecture (U) |
| eurex/dataaccess/common | gts.eurex.dataaccess.common | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| eurex/dataaccess/commondb-database | gts.eurex.dataaccess.commondb-database | AD Trading Architecture (U) |
| eurex/dataaccess/commondb-database-conversion | gts.eurex.dataaccess.commondb-database-conversion | AD Trading Architecture (U) |
| eurex/dataaccess/cross-partition-data | gts.eurex.dataaccess.cross-partition-data | AD Trading Architecture (U) |
| eurex/dataaccess/database-tools | gts.eurex.dataaccess.database-tools | AD Trading Architecture (U) |
| eurex/dataaccess/exportdb-database | gts.eurex.dataaccess.exportdb-database | AD Trading Architecture (U) |
| eurex/dataaccess/mysql-configurations | gts.eurex.dataaccess.mysql-configurations | AD Trading Architecture (U) |
| eurex/dataaccess/mysql-db-clean-config | gts.eurex.dataaccess.mysql-db-clean-config | AD Trading Architecture (U) |
| eurex/dataaccess/mysql-db-users | gts.eurex.dataaccess.mysql-db-users | AD Trading Architecture (U) |
| eurex/dataaccess/mysql-scripts | gts.eurex.dataaccess.mysql-scripts | AD Trading Architecture (U) |
| eurex/dataaccess/rda-common | gts.eurex.dataaccess.rda-common | AD Trading Architecture (U) |
| eurex/dataaccess/rda-outbound-bridge | gts.eurex.dataaccess.rda-outbound-bridge | AD Trading Architecture (U) |
| eurex/dataaccess/rdb-database | gts.eurex.dataaccess.rdb-database | AD Trading Architecture (U) |
| eurex/dataaccess/rdsgen-transformation | gts.eurex.dataaccess.rdsgen-transformation | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| eurex/dataaccess/tradeentryservice | gts.eurex.dataaccess.tradeentryservice | AD Trading Prague (U) |
| eurex/dataaccess/viewdb-database | gts.eurex.dataaccess.viewdb-database | AD Trading Architecture (U) |
| eurex/gateway/common | gts.eurex.gateway.common | AD Interface Design & Gateways (U) |
| eurex/gateway/edci | gts.eurex.gateway.edci | AD Interface Design & Gateways (U) |
| eurex/gateway/edci-docu | gts.eurex.gateway.edci-docu | AD Trading Architecture (U) |
| eurex/gateway/eti | gts.eurex.gateway.eti | AD Interface Design & Gateways (U) |
| eurex/gateway/eurfixdocu | gts.eurex.gateway.eurfixdocu | AD Trading Architecture (U) |
| eurex/gateway/fix | gts.eurex.gateway.fix | AD Interface Design & Gateways (U) |
| eurex/gateway/fixdocu | gts.eurex.gateway.fixdocu | AD Trading Architecture (U) |
| eurex/gateway/fixgw | gts.eurex.gateway.fixgw | AD Interface Design & Gateways (U) |
| eurex/gateway/fixgw-rule_gen | gts.eurex.gateway.fixgw-rule_gen | AD Interface Design & Gateways (U) |
| eurex/gateway/fixgwconversion | gts.eurex.gateway.fixgwconversion | AD Interface Design & Gateways (U) |
| eurex/gateway/funcvalapi | gts.eurex.gateway.funcvalapi | AD Trading Core (U) |
| eurex/gateway/gameinterface | gts.eurex.gateway.gameinterface | AD Interface Design & Gateways (U) |
| eurex/gateway/gateway | gts.eurex.gateway.gateway | AD Interface Design & Gateways (U) |
| eurex/gateway/gwconversion | gts.eurex.gateway.gwconversion | AD Interface Design & Gateways (U) |
| eurex/gateway/odcgw | gts.eurex.gateway.odcgw | AD Interface Design & Gateways (U) |
| eurex/gateway/odcgwconversion | gts.eurex.gateway.odcgwconversion | AD Interface Design & Gateways (U) |
| eurex/gateway/oficonversion | gts.eurex.gateway.oficonversion | AD Interface Design & Gateways (U) |
| eurex/gateway/outboundfi | gts.eurex.gateway.outboundfi | AD Interface Design & Gateways (U) |
| eurex/gateway/outboundfi-docu | gts.eurex.gateway.outboundfi-docu | AD Interface Design & Gateways (U) |
| eurex/int/requirements | gts.eurex.int.requirements | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| eurex/int/smoketest | gts.eurex.int.smoketest | AD Trading Architecture (U) |
| eurex/intmsg/documentation | gts.eurex.intmsg.documentation | RDS & Controller (U) |
| eurex/intmsg/model/apphost | gts.eurex.intmsg.model.apphost | AD Trading Architecture (U) |
| eurex/intmsg/model/apps | gts.eurex.intmsg.model.apps | AD Trading Core (U) |
| eurex/intmsg/model/basic | gts.eurex.intmsg.model.basic | AD Trading Core (U) |
| eurex/intmsg/model/bond | gts.eurex.intmsg.model.bond | AD Trading Architecture (U) |
| eurex/intmsg/model/configspecific | gts.eurex.intmsg.model.configspecific | AD Trading Architecture (U) |
| eurex/intmsg/model/contractmanager | gts.eurex.intmsg.model.contractmanager | AD Trading Architecture (U) |
| eurex/intmsg/model/data-distributor-common | gts.eurex.intmsg.model.data-distributor-common | AD Trading Core (U) |
| eurex/intmsg/model/fixgw | gts.eurex.intmsg.model.fixgw | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/gateway | gts.eurex.intmsg.model.gateway | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/liquidity-discovery-service | gts.eurex.intmsg.model.liquidity-discovery-service | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/matcher | gts.eurex.intmsg.model.matcher | AD Trading Core (U) |
| eurex/intmsg/model/multicaster | gts.eurex.intmsg.model.multicaster | AD Trading Core (U) |
| eurex/intmsg/model/odc | gts.eurex.intmsg.model.odc | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/outboundfi | gts.eurex.intmsg.model.outboundfi | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/referencedata | gts.eurex.intmsg.model.referencedata | AD Trading Architecture (U) |
| eurex/intmsg/model/trade-feed-handler | gts.eurex.intmsg.model.trade-feed-handler | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/trade-feed-handler-internal | gts.eurex.intmsg.model.trade-feed-handler-internal | AD Interface Design & Gateways (U) |
| eurex/intmsg/model/tradeentryservice | gts.eurex.intmsg.model.tradeentryservice | AD Trading Prague (U) |
| eurex/intmsg/model/trademanager | gts.eurex.intmsg.model.trademanager | AD Trading Core (U) |
| eurex/intmsg/model/tradestats | gts.eurex.intmsg.model.tradestats | Integr.,Configur.Mgmt&Dev.OpsTool (U) |
| eurex/messaging | gts.eurex.messaging | AD Trading Architecture (U) |
| eurex/release | gts.eurex.release | Integr.,Configur.Mgmt&Dev.OpsTool |
| eurex/service/disaster-recovery | gts.eurex.service.disaster-recovery | AD Trading Architecture (U) |
| eurex/service/jobschedule | gts.eurex.service.jobschedule | AD Trading Architecture (U) |
| eurex/service/opertools | gts.eurex.service.opertools | AD Trading Architecture (U) |
| eurex/service/qpid-setup | gts.eurex.service.qpid-setup | AD Trading Architecture (U) |
| eurex/service/sanity_checks | gts.eurex.service.sanity_checks | AD Trading Architecture (U) |
| eurex/service/setup | gts.eurex.service.setup | AD Trading Architecture (U) |
| eurex/specification/view-model | gts.eurex.specification.view-model | AD Trading Architecture (U) |
| eurex/test/functional/sample-refdata | gts.eurex.test.functional.sample-refdata | TIED: AD Trading Architecture (U)/Integr.,Configur.Mgmt&Dev.OpsTool (U)/Payment & FX Settlement AD (U)/Quality Assurance (U)/Repo Trading Functionality & Quality Assurance (U)/Xetra/Eurex Clearing Applications Administration (U) |
| eurex/test/functional/sample-refdata-nodal | gts.eurex.test.functional.sample-refdata-nodal | AD Trading RDS (U) |
| perfmon/ackstat | gts.perfmon.ackstat | AD OPM & Cloud Simulation (U) |
| perfmon/capture | gts.perfmon.capture | AD OPM & Cloud Simulation (U) |
| perfmon/core | gts.perfmon.core | AD OPM & Cloud Simulation (U) |
| perfmon/ipasm | gts.perfmon.ipasm | AD OPM & Cloud Simulation (U) |
| perfmon/market-data-reader | gts.perfmon.market-data-reader | AD OPM & Cloud Simulation (U) |
| perfmon/monsoapproxy | gts.perfmon.monsoapproxy | AD OPM & Cloud Simulation (U) |
| tsa/pcapdump | gts.tsa.pcapdump | Trading System Analytics (U) |
