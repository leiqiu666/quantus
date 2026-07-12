# Tushare 数据接入进度

> 盘点日期：2026-07-08（P0 九项全链路更新）
> Tushare 文档来源：[`.claude/skills/get_tushare_doc/doc_index.json`](../.claude/skills/get_tushare_doc/doc_index.json)（本地索引 **237** 篇，其中 **233** 个带 `api_name`）
> 分类口径：沿用 [`ETL模块分类与命名规范.md`](ETL模块分类与命名规范.md) 的 **6 大域** + 文档 §扩展预留 的 **扩展域**；Admin 看板 **7 组**见 [`completeness_dashboard_config.py`](../src/service/etl/completeness_dashboard_config.py)
> 查文档：`uv run python .claude/skills/get_tushare_doc/tushare_doc.py search "<接口名>" -d`

---

## 1. 总览

| 维度 | 数量 | 说明 |
|------|------|------|
| Tushare 文档/API（本地索引） | 237 / 233 | 全库接口面 |
| **Quantus 已接入数据源管线** | **29** | ETL/Research 有完整 pull +（多数）完整性 |
| 部分接入 | 1 | 有 ETL，未进 Admin 看板完整性 |
| 衍生（非 Tushare 直拉） | 1 | 如 `stock_active_count` |
| 未接入（Tushare API 粒度） | 204 | 见 §4 分域附录 |

**说明**：Quantus 以「**语义化表名 / 数据源管线**」计数（约 22 条），不是 Tushare API 个数。一条管线可覆盖多个 API（如龙虎榜 = `top_list` + `top_inst`；财报 = 4×VIP + 4×by-code 补位）。

---

## 2. 已接入清单（按域）

| 域 | 数据源 | DB 表 / 存储 | Tushare API | ETL / Research | Admin 看板 group | 状态 |
|----|--------|-------------|-------------|----------------|------------------|------|
| `stock_` | A股股票列表 | `stock_list` | stock_basic | `stock pull-list-a` | — | ✅ done |  |
| `stock_` | 交易日历 | `stock_trade_calendar` | trade_cal | `trade-cal pull-history` | — | ✅ done |  |
| `stock_` | 停复牌 | `stock_suspend` | suspend_d | `suspend pull-by-date` | `stock_basic_trade_date` | ✅ done |  |
| `stock_` | 活跃股票数 | `stock_active_count` | — | `stock refresh-active-count` | `多组分母` | 🔧 derived | 本地聚合，非 Tushare 直拉 |
| `kline_` | 日K + 涨跌停 | `kline_daily` | daily, stk_limit | `kline pull-daily / pull-stk-limit` | `kline_trade_date` | ✅ done | 涨跌停价融合进 kline_daily |
| `kline_` | 复权因子 | `kline_daily.adj_factor` | adj_factor | `kline pull-adj-factor` | `kline_trade_date` | ✅ done |  |
| `kline_` | 技术因子 PG | `kline_stock_factor` | stk_factor_pro | `stk-factor pull-by-date-range` | `kline_trade_date` | ✅ done | MACD/KDJ 等少量字段 |
| `kline_` | 技术因子 Parquet | `warehouse/factor/*` | stk_factor_pro | `research tushare-factor` | — | ✅ done | 93 因子宽表，Research 路径 |
| `financial_` | 财报三表+指标 | `financial_report_*` | income/balance/cashflow/fina_indicator (+vip) | `report report-history-init` | `financial_report_period` | ✅ done | 补位用 by-code 接口 |
| `financial_` | 业绩预告 | `financial_forecast` | forecast_vip | `financial_forecast pull-by-period` | `financial_report_period` | ✅ done |  |
| `financial_` | 业绩快报 | `financial_express` | express_vip | `financial_express pull-by-period` | `financial_report_period` | ✅ done |  |
| `financial_` | 审计意见 | `financial_audit` | fina_audit | `audit pull-by-period` | `financial_report_period` | ✅ done | 仅年报 |
| `financial_` | 前十大股东 | `financial_shareholder_top10` | top10_holders | `shareholder pull-by-date` | `financial_ann_date` | ✅ done |  |
| `financial_` | 股东户数 | `financial_stock_holder` | stk_holdernumber | `stk-holder pull-number` | `financial_ann_date` | ✅ done |  |
| `market_` | 每日指标 | `market_daily_basic` | daily_basic | `daily-basic pull-by-date-range` | `market_trade_date` | ✅ done | PE/PB/市值/换手 |
| `market_` | 分红送股 | `market_dividend` | dividend | `market_dividend pull-by-date-range` | — | ⚠️ partial | 有 ETL；未进完整性看板 |
| `market_` | 资金流向 | `market_moneyflow` | moneyflow | `market_moneyflow pull-by-date-range` | `market_trade_date` | ✅ done |  |
| `market_` | 融资融券明细 | `market_margin_detail` | margin_detail | `margin pull-detail-by-date-range` | `market_trade_date` | ✅ done |  |
| `market_` | 北向十大成交 | `market_northbound_top10` | hsgt_top10 | `hsgt pull-top10-by-date-range` | `market_trade_date` | ✅ done | 非全量持股 |
| `market_` | 龙虎榜 | `market_dragon_tiger_*` | top_list, top_inst | `dragon-tiger pull-by-date-range` | `market_trade_date` | ✅ done |  |
| `market_` | 大宗交易 | `market_block_trade` | block_trade | `block-trade pull-by-date-range` | `market_trade_date` | ✅ done |  |
| `index_` | 指数成分权重 | `index_weight` | index_weight | `index pull-weight-by-month-range` | `index_month` | ✅ done | 沪深300/500/1000/创业板指 |
| `index_` | 指数基本信息 | `index_basic` | index_basic | `index pull-basic-snapshot` | `index_month` | ✅ done | 快照，SSE pull-only |
| `index_` | 申万行业分类 | `index_classify` | index_classify | `index pull-classify-snapshot` | `index_month` | ✅ done | L1/L2/L3 × SW2021 |
| `index_` | 申万行业成分 | `index_member_all` | index_member_all | `index pull-member-all-snapshot` | `index_month` | ✅ done | is_new=Y 全量 |
| `index_` | 指数日线 | `index_daily` | index_daily | `index pull-daily-by-code-range` | `index_trade_date` | ✅ done | 基准指数 × 交易日 |
| `stock_` | 盘前股本 | `stock_premarket` | stk_premarket | `stock_premarket pull-by-date-range` | `stock_basic_trade_date` | ✅ done | 总/流通股本、涨跌停价 |
| `stock_` | 限售解禁 | `stock_share_float` | share_float | `stock_share_float pull-by-date` | `stock_basic_trade_date` | ✅ done | 按 float_date |
| `market_` | 沪深港通资金 | `market_moneyflow_hsgt` | moneyflow_hsgt | `market_hsgt pull-by-date-range` | `market_trade_date` | ✅ done | 北向/南向日频汇总 |
| `market_` | 港股通持股 | `market_hk_hold` | hk_hold | `market_hk_hold pull-by-date-range` | `market_trade_date` | ✅ done | 北向持股明细 |
| `financial_` | 披露计划 | `financial_disclosure_date` | disclosure_date | `financial_disclosure_date pull-by-period` | `financial_report_period` | ✅ done | PEAD 事件时点 |
| `financial_` | 前十大流通股东 | `financial_top10_floatholders` | top10_floatholders | `shareholder pull-floatholders-by-date` | `financial_ann_date` | ✅ done |  |
| `financial_` | 主营业务构成 | `financial_fina_mainbz` | fina_mainbz_vip | `financial_fina_mainbz pull-by-period` | `financial_report_period` | ✅ done | 按报告期 VIP |

图例：✅ 已接入 · ⚠️ 部分 · 🔧 衍生聚合

### Admin 看板 ↔ 域 对照

| Admin group_id | 域 | 已接入列 |
|--------------|-----|---------|
| `financial_report_period` | financial_ + 部分 market_ | 三表/指标/预告/快报/审计/披露计划/主营构成 |
| `financial_ann_date` | financial_ | 股东户数、前十大股东、前十大流通股东 |
| `kline_trade_date` | kline_ | 日K、复权、涨跌停、技术因子 |
| `market_trade_date` | market_ | 每日指标、资金流、两融、北向十大、龙虎榜、大宗、沪深港通资金、港股通持股 |
| `index_month` | index_ | 指数权重、基本信息、申万分类、申万成分 |
| `index_trade_date` | index_ | 指数日线 |
| `stock_basic_trade_date` | stock_ | 停复牌、盘前股本、限售解禁 |

---

## 3. 量化视角 · 接入优先级（建议）

依据 [`量化层完整方案.md`](量化层完整方案.md) Phase 1–2（因子 / 截面回测）与当前基座缺口。

### P0 · 截面因子 / 回测基座

下一阶段最该补，直接支撑 Phase 2 截面回测与因子合成

| 域 | API / 能力 | 用途 | 状态 |
|----|-----------|------|------|
| `index_` | `index_daily` | 指数日线 — 基准收益、Beta、市场状态划分 | ✅ 2026-07-08 |
| `index_` | `index_basic` | 指数基本信息 — universe / 基准映射 | ✅ 2026-07-08 |
| `index_` | `index_classify + index_member_all` | 申万行业 — 行业中性、行业因子 | ✅ 2026-07-08 |
| `market_` | `moneyflow_hsgt` | 沪深港通资金流向 — 补全北向维度（现仅有 hsgt_top10） | ✅ 2026-07-08 |
| `market_` | `hk_hold` | 沪深港股通持股明细 — 北向持仓因子 | ✅ 2026-07-08 |
| `stock_` | `share_float + stk_premarket` | 流通股本 / 盘前股本 — 精确市值、换手分母 | ✅ 2026-07-08 |
| `financial_` | `fina_mainbz` | 主营业务构成 — 基本面行业/产品暴露 | ✅ 2026-07-08 |
| `financial_` | `disclosure_date` | 财报披露计划 — 事件驱动 PEAD 时点 | ✅ 2026-07-08 |
| `financial_` | `top10_floatholders` | 前十大流通股东 — 筹码/治理因子 | ✅ 2026-07-08 |
| `kline_` | `stk_mins` | 分钟线 — 量化方案 Phase 3+，可先落 Parquet | ⏳ 未做 |

### P1 · 事件与另类 Alpha

丰富 event / 另类因子，非阻塞主链路

| 域 | API / 能力 | 用途 |
|----|-----------|------|
| `market_` | `margin` | 融资融券汇总 — 杠杆情绪（现仅有 margin_detail） |
| `market_` | `cyq_perf / cyq_chips` | 筹码分布 — 技术另类因子 |
| `other_` | `stk_holdertrade` | 股东增减持 — 内部人交易事件 |
| `other_` | `repurchase / new_share` | 回购 / IPO — 公司行为事件 |
| `other_` | `report_rc` | 卖方盈利预测 — 预期因子 |
| `market_` | `stk_surv` | 机构调研 — 关注度因子 |
| `other_` | `anns_d` | 全量公告 — 事件驱动 NLP 前置 |

### P2 · 扩资产类别

A 股主线稳定后再扩

| 域 | API / 能力 | 用途 |
|----|-----------|------|
| `fund_` | `fund_daily / etf_basic` | ETF — ETF 策略、行业 ETF 轮动 |
| `bond_` | `cb_daily / cb_basic` | 可转债 — 可转债量化 |
| `index_` | `idx_factor_pro` | 指数技术因子 — 与 stk_factor_pro 对称 |
| `macro_` | `cn_gdp / cn_m / cn_pmi` | 宏观 — 宏观择时、风险预算 |
| `hk_` | `hk_daily` | 港股 — AH 溢价扩展 |

### P3 · 低优先 / 非 A 股主线

除非策略明确需要

| 域 | API / 能力 | 用途 |
|----|-----------|------|
| `future_` | `fut_daily` | 期货 — CTA / 对冲 |
| `option_` | `opt_daily` | 期权 — 波动率策略 |
| `us_` | `us_daily` | 美股 — 全球配置 |
| `other_` | `news / major_news` | 新闻资讯 — 需 NLP 管线，方案中标记未来 |

**已覆盖、短期不必重复接**：日 K + 复权 + 涨跌停、财报三表+指标、停复牌/日历/列表、`daily_basic`、`moneyflow`、`margin_detail`、`stk_factor_pro`（PG + Parquet 双路径）、龙虎榜/大宗、指数权重。

---

## 4. Tushare 全库分域附录（接入状态）

以下按 **§2 相同分类逻辑** 列出本地索引中的接口；✅ = 已在 Quantus 管线中使用。

### stock_ 股票基础（✅ 3 · ⚠️ 0 · ❌ 14 / 17）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ✅ | `stock_basic` | 股票基础信息 | [25](https://tushare.pro/document/2?doc_id=25) |
| ✅ | `suspend_d` | 每日停复牌信息 | [214](https://tushare.pro/document/2?doc_id=214) |
| ✅ | `trade_cal` | 交易日历 | [26](https://tushare.pro/document/2?doc_id=26) |
| ❌ | `bak_basic` | 股票历史列表（历史每天股票列表） | [262](https://tushare.pro/document/2?doc_id=262) |
| ❌ | `fut_trade_cal` | 交易日历 | [467](https://tushare.pro/document/2?doc_id=467) |
| ❌ | `hk_tradecal` | 港股交易日历 | [250](https://tushare.pro/document/2?doc_id=250) |
| ❌ | `namechange` | 股票曾用名 | [100](https://tushare.pro/document/2?doc_id=100) |
| ❌ | `new_share` | IPO新股列表 | [123](https://tushare.pro/document/2?doc_id=123) |
| ❌ | `pledge_detail` | 股权质押明细 | [111](https://tushare.pro/document/2?doc_id=111) |
| ❌ | `pledge_stat` | 股权质押统计数据 | [110](https://tushare.pro/document/2?doc_id=110) |
| ❌ | `repurchase` | 股票回购 | [124](https://tushare.pro/document/2?doc_id=124) |
| ❌ | `share_float` | 限售股解禁 | [160](https://tushare.pro/document/2?doc_id=160) |
| ❌ | `stk_premarket` | 股本情况（盘前） | [329](https://tushare.pro/document/2?doc_id=329) |
| ❌ | `stock_company` | 上市公司基本信息 | [112](https://tushare.pro/document/2?doc_id=112) |
| ❌ | `stock_hsgt` | 沪深港通股票列表 | [398](https://tushare.pro/document/2?doc_id=398) |
| ❌ | `stock_st` | ST股票列表 | [397](https://tushare.pro/document/2?doc_id=397) |
| ❌ | `us_tradecal` | 美股交易日历 | [253](https://tushare.pro/document/2?doc_id=253) |

### kline_ 行情域（✅ 4 · ⚠️ 0 · ❌ 30 / 34）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ✅ | `adj_factor` | 复权因子 | [28](https://tushare.pro/document/2?doc_id=28) |
| ✅ | `daily` | A股日线行情 | [27](https://tushare.pro/document/2?doc_id=27) |
| ✅ | `stk_factor_pro` | 股票技术面因子(专业版) | [328](https://tushare.pro/document/2?doc_id=328) |
| ✅ | `stk_limit` | 每日涨跌停价格 | [183](https://tushare.pro/document/2?doc_id=183) |
| ❌ | `(文档无 api_name)` | A股复权行情 | [146](https://tushare.pro/document/2?doc_id=146) |
| ❌ | `bak_daily` | 备用行情 | [255](https://tushare.pro/document/2?doc_id=255) |
| ❌ | `ci_daily` | 中信行业指数行情 | [308](https://tushare.pro/document/2?doc_id=308) |
| ❌ | `daily_info` | 市场交易统计 | [215](https://tushare.pro/document/2?doc_id=215) |
| ❌ | `dc_daily` | 概念板块行情 | [382](https://tushare.pro/document/2?doc_id=382) |
| ❌ | `fx_daily` | 外汇日线行情 | [179](https://tushare.pro/document/2?doc_id=179) |
| ❌ | `idx_mins` | 指数历史分钟行情 | [419](https://tushare.pro/document/2?doc_id=419) |
| ❌ | `limit_list_d` | 涨跌停列表（新） | [298](https://tushare.pro/document/2?doc_id=298) |
| ❌ | `limit_list_ths` | 涨跌停榜单（同花顺） | [355](https://tushare.pro/document/2?doc_id=355) |
| ❌ | `monthly` | 月线行情 | [145](https://tushare.pro/document/2?doc_id=145) |
| ❌ | `repo_daily` | 债券回购日行情 | [256](https://tushare.pro/document/2?doc_id=256) |
| ❌ | `report_rc` | 卖方盈利预测数据 | [292](https://tushare.pro/document/2?doc_id=292) |
| ❌ | `rt_hk_k` | 港股实时日线 | [383](https://tushare.pro/document/2?doc_id=383) |
| ❌ | `rt_idx_k` | 指数实时日线 | [403](https://tushare.pro/document/2?doc_id=403) |
| ❌ | `rt_idx_min` | A股实时分钟 | [420](https://tushare.pro/document/2?doc_id=420) |
| ❌ | `rt_k` | A股实时日线 | [372](https://tushare.pro/document/2?doc_id=372) |
| ❌ | `rt_min` | A股实时分钟 | [374](https://tushare.pro/document/2?doc_id=374) |
| ❌ | `rt_min_daily` | A股实时分钟-日累计 | [457](https://tushare.pro/document/2?doc_id=457) |
| ❌ | `rt_sw_k` | 申万实时行情 | [417](https://tushare.pro/document/2?doc_id=417) |
| ❌ | `sge_daily` | 现货黄金日行情 | [285](https://tushare.pro/document/2?doc_id=285) |
| ❌ | `stk_factor` | 股票技术因子（量化因子） | [296](https://tushare.pro/document/2?doc_id=296) |
| ❌ | `stk_mins` | 股票历史分钟行情 | [370](https://tushare.pro/document/2?doc_id=370) |
| ❌ | `stk_week_month_adj` | 股票周/月线行情(复权--每日更新) | [365](https://tushare.pro/document/2?doc_id=365) |
| ❌ | `stk_weekly_monthly` | 股票周/月线行情(每日更新) | [336](https://tushare.pro/document/2?doc_id=336) |
| ❌ | `sw_daily` | 申万行业日线行情 | [327](https://tushare.pro/document/2?doc_id=327) |
| ❌ | `sw_mins` | SW历史分钟 | [469](https://tushare.pro/document/2?doc_id=469) |
| ❌ | `sz_daily_info` | 深圳市场每日交易概况 | [268](https://tushare.pro/document/2?doc_id=268) |
| ❌ | `tdx_daily` | TDX板块行情 | [378](https://tushare.pro/document/2?doc_id=378) |
| ❌ | `ths_daily` | 板块指数行情 | [260](https://tushare.pro/document/2?doc_id=260) |
| ❌ | `weekly` | 周线行情 | [144](https://tushare.pro/document/2?doc_id=144) |

### financial_ 财务域（✅ 8 · ⚠️ 0 · ❌ 5 / 13）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ✅ | `cashflow` | 现金流量表 | [44](https://tushare.pro/document/2?doc_id=44) |
| ✅ | `express` | 业绩快报 | [46](https://tushare.pro/document/2?doc_id=46) |
| ✅ | `fina_audit` | 财务审计意见 | [80](https://tushare.pro/document/2?doc_id=80) |
| ✅ | `fina_indicator` | 财务指标数据 | [79](https://tushare.pro/document/2?doc_id=79) |
| ✅ | `forecast` | 业绩预告 | [45](https://tushare.pro/document/2?doc_id=45) |
| ✅ | `income` | 利润表 | [33](https://tushare.pro/document/2?doc_id=33) |
| ✅ | `stk_holdernumber` | 股东人数 | [166](https://tushare.pro/document/2?doc_id=166) |
| ✅ | `top10_holders` | 前十大股东 | [61](https://tushare.pro/document/2?doc_id=61) |
| ❌ | `balancesheet` | 资产负债表 | [36](https://tushare.pro/document/2?doc_id=36) |
| ❌ | `disclosure_date` | 财报披露计划 | [162](https://tushare.pro/document/2?doc_id=162) |
| ❌ | `fina_mainbz` | 主营业务构成 | [81](https://tushare.pro/document/2?doc_id=81) |
| ❌ | `mkt_idx_bmk` | 基金业绩基准 | [462](https://tushare.pro/document/2?doc_id=462) |
| ❌ | `top10_floatholders` | 前十大流通股东 | [62](https://tushare.pro/document/2?doc_id=62) |

### market_ 市场指标（✅ 8 · ⚠️ 0 · ❌ 16 / 24）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ✅ | `block_trade` | 大宗交易 | [161](https://tushare.pro/document/2?doc_id=161) |
| ✅ | `daily_basic` | 每日指标 | [32](https://tushare.pro/document/2?doc_id=32) |
| ✅ | `dividend` | 分红送股 | [103](https://tushare.pro/document/2?doc_id=103) |
| ✅ | `hsgt_top10` | 沪深股通十大成交股 | [48](https://tushare.pro/document/2?doc_id=48) |
| ✅ | `margin_detail` | 融资融券交易明细 | [59](https://tushare.pro/document/2?doc_id=59) |
| ✅ | `moneyflow` | 个股资金流向 | [170](https://tushare.pro/document/2?doc_id=170) |
| ✅ | `top_inst` | 龙虎榜机构明细 | [107](https://tushare.pro/document/2?doc_id=107) |
| ✅ | `top_list` | 龙虎榜每日明细 | [106](https://tushare.pro/document/2?doc_id=106) |
| ❌ | `broker_recommend` | 券商每月荐股 | [267](https://tushare.pro/document/2?doc_id=267) |
| ❌ | `cyq_chips` | 每日筹码分布 | [294](https://tushare.pro/document/2?doc_id=294) |
| ❌ | `cyq_perf` | 每日筹码及胜率 | [293](https://tushare.pro/document/2?doc_id=293) |
| ❌ | `margin` | 融资融券交易汇总 | [58](https://tushare.pro/document/2?doc_id=58) |
| ❌ | `margin_secs` | 融资融券标的（盘前更新） | [326](https://tushare.pro/document/2?doc_id=326) |
| ❌ | `moneyflow_cnt_ths` | 同花顺概念板块资金流向（THS） | [371](https://tushare.pro/document/2?doc_id=371) |
| ❌ | `moneyflow_dc` | 个股资金流向（DC） | [349](https://tushare.pro/document/2?doc_id=349) |
| ❌ | `moneyflow_hsgt` | 沪深港通资金流向 | [47](https://tushare.pro/document/2?doc_id=47) |
| ❌ | `moneyflow_ind_dc` | 东财概念及行业板块资金流向（DC） | [344](https://tushare.pro/document/2?doc_id=344) |
| ❌ | `moneyflow_ind_ths` | 同花顺行业资金流向（THS） | [343](https://tushare.pro/document/2?doc_id=343) |
| ❌ | `moneyflow_mkt_dc` | 大盘资金流向（DC） | [345](https://tushare.pro/document/2?doc_id=345) |
| ❌ | `moneyflow_ths` | 个股资金流向（THS） | [348](https://tushare.pro/document/2?doc_id=348) |
| ❌ | `stk_auction` | 当日集合竞价 | [369](https://tushare.pro/document/2?doc_id=369) |
| ❌ | `stk_auction_c` | 股票收盘集合竞价数据 | [354](https://tushare.pro/document/2?doc_id=354) |
| ❌ | `stk_auction_o` | 股票开盘集合竞价数据 | [353](https://tushare.pro/document/2?doc_id=353) |
| ❌ | `stk_surv` | 机构调研表 | [275](https://tushare.pro/document/2?doc_id=275) |

### index_ 指数域（✅ 1 · ⚠️ 0 · ❌ 10 / 11）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ✅ | `index_weight` | 指数成分和权重 | [96](https://tushare.pro/document/2?doc_id=96) |
| ❌ | `idx_factor_pro` | 指数技术因子(专业版) | [358](https://tushare.pro/document/2?doc_id=358) |
| ❌ | `index_basic` | 指数基本信息 | [94](https://tushare.pro/document/2?doc_id=94) |
| ❌ | `index_classify` | 申万行业分类 | [181](https://tushare.pro/document/2?doc_id=181) |
| ❌ | `index_daily` | 指数日线行情 | [95](https://tushare.pro/document/2?doc_id=95) |
| ❌ | `index_dailybasic` | 大盘指数每日指标 | [128](https://tushare.pro/document/2?doc_id=128) |
| ❌ | `index_global` | 国际指数 | [211](https://tushare.pro/document/2?doc_id=211) |
| ❌ | `index_member_all` | 申万行业成分构成(分级) | [335](https://tushare.pro/document/2?doc_id=335) |
| ❌ | `index_monthly` | 指数月线行情 | [172](https://tushare.pro/document/2?doc_id=172) |
| ❌ | `index_weekly` | 指数周线行情 | [171](https://tushare.pro/document/2?doc_id=171) |
| ❌ | `ths_index` | 概念和行业指数 | [259](https://tushare.pro/document/2?doc_id=259) |

### reference_ 参考/分类（扩展）（✅ 0 · ⚠️ 0 · ❌ 10 / 10）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `dc_concept` | 题材数据（DC） | [421](https://tushare.pro/document/2?doc_id=421) |
| ❌ | `dc_concept_cons` | 题材成分（DC） | [422](https://tushare.pro/document/2?doc_id=422) |
| ❌ | `dc_hot` | DC热榜 | [321](https://tushare.pro/document/2?doc_id=321) |
| ❌ | `dc_index` | 概念板块 | [362](https://tushare.pro/document/2?doc_id=362) |
| ❌ | `dc_member` | 板块成分 | [363](https://tushare.pro/document/2?doc_id=363) |
| ❌ | `limit_cpt_list` | 最强板块统计 | [357](https://tushare.pro/document/2?doc_id=357) |
| ❌ | `tdx_index` | TDX板块信息 | [376](https://tushare.pro/document/2?doc_id=376) |
| ❌ | `tdx_member` | TDX板块成分 | [377](https://tushare.pro/document/2?doc_id=377) |
| ❌ | `ths_hot` | THS热榜 | [320](https://tushare.pro/document/2?doc_id=320) |
| ❌ | `ths_member` | 概念板块成分 | [261](https://tushare.pro/document/2?doc_id=261) |

### fund_ 基金（扩展）（✅ 0 · ⚠️ 0 · ❌ 18 / 18）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `etf_basic` | ETF基础信息 | [385](https://tushare.pro/document/2?doc_id=385) |
| ❌ | `etf_index` | ETF基准指数列表 | [386](https://tushare.pro/document/2?doc_id=386) |
| ❌ | `etf_mins` | ETF历史分钟行情 | [387](https://tushare.pro/document/2?doc_id=387) |
| ❌ | `etf_share_size` | ETF份额规模 | [408](https://tushare.pro/document/2?doc_id=408) |
| ❌ | `fund_adj` | 基金复权因子 | [199](https://tushare.pro/document/2?doc_id=199) |
| ❌ | `fund_basic` | 公募基金列表 | [19](https://tushare.pro/document/2?doc_id=19) |
| ❌ | `fund_company` | 公募基金公司 | [118](https://tushare.pro/document/2?doc_id=118) |
| ❌ | `fund_daily` | ETF日线行情 | [127](https://tushare.pro/document/2?doc_id=127) |
| ❌ | `fund_div` | 公募基金分红 | [120](https://tushare.pro/document/2?doc_id=120) |
| ❌ | `fund_factor_pro` | 场内基金技术因子(专业版) | [359](https://tushare.pro/document/2?doc_id=359) |
| ❌ | `fund_manager` | 基金经理 | [208](https://tushare.pro/document/2?doc_id=208) |
| ❌ | `fund_nav` | 公募基金净值 | [119](https://tushare.pro/document/2?doc_id=119) |
| ❌ | `fund_portfolio` | 公募基金持仓数据 | [121](https://tushare.pro/document/2?doc_id=121) |
| ❌ | `fund_share` | 基金规模数据 | [207](https://tushare.pro/document/2?doc_id=207) |
| ❌ | `rt_etf_k` | ETF实时日线 | [400](https://tushare.pro/document/2?doc_id=400) |
| ❌ | `rt_etf_min` | ETF实时分钟 | [416](https://tushare.pro/document/2?doc_id=416) |
| ❌ | `rt_etf_min_daily` | ETF实时分钟-日累计 | [470](https://tushare.pro/document/2?doc_id=470) |
| ❌ | `rt_etf_sz_iopv` | ETF实时参考 | [454](https://tushare.pro/document/2?doc_id=454) |

### bond_ 债券（扩展）（✅ 0 · ⚠️ 0 · ❌ 10 / 10）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `cb_basic` | 可转债基本信息 | [185](https://tushare.pro/document/2?doc_id=185) |
| ❌ | `cb_call` | 可转债赎回信息 | [269](https://tushare.pro/document/2?doc_id=269) |
| ❌ | `cb_daily` | 可转债行情 | [187](https://tushare.pro/document/2?doc_id=187) |
| ❌ | `cb_factor_pro` | 可转债技术因子(专业版) | [392](https://tushare.pro/document/2?doc_id=392) |
| ❌ | `cb_issue` | 可转债发行 | [186](https://tushare.pro/document/2?doc_id=186) |
| ❌ | `cb_price_chg` | 可转债转股价变动 | [246](https://tushare.pro/document/2?doc_id=246) |
| ❌ | `cb_rate` | 可转债票面利率 | [305](https://tushare.pro/document/2?doc_id=305) |
| ❌ | `cb_rating` | 可转债债券评级 | [458](https://tushare.pro/document/2?doc_id=458) |
| ❌ | `cb_share` | 可转债转股结果 | [247](https://tushare.pro/document/2?doc_id=247) |
| ❌ | `top10_cb_holders` | 可转债十大持有人 | [459](https://tushare.pro/document/2?doc_id=459) |

### future_ 期货（扩展）（✅ 0 · ⚠️ 0 · ❌ 13 / 13）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `(文档无 api_name)` | 期货Tick行情数据 | [314](https://tushare.pro/document/2?doc_id=314) |
| ❌ | `ft_limit` | 期货合约涨跌停价格（盘前） | [368](https://tushare.pro/document/2?doc_id=368) |
| ❌ | `ft_mins` | 期货历史分钟行情 | [313](https://tushare.pro/document/2?doc_id=313) |
| ❌ | `fut_basic` | 期货合约信息表 | [135](https://tushare.pro/document/2?doc_id=135) |
| ❌ | `fut_daily` | 期货日线行情 | [138](https://tushare.pro/document/2?doc_id=138) |
| ❌ | `fut_holding` | 每日成交持仓排名 | [139](https://tushare.pro/document/2?doc_id=139) |
| ❌ | `fut_index_daily` | 南华期货指数日线行情 | [468](https://tushare.pro/document/2?doc_id=468) |
| ❌ | `fut_mapping` | 期货主力与连续合约 | [189](https://tushare.pro/document/2?doc_id=189) |
| ❌ | `fut_settle` | 结算参数 | [141](https://tushare.pro/document/2?doc_id=141) |
| ❌ | `fut_weekly_detail` | 期货主要品种交易周报 | [216](https://tushare.pro/document/2?doc_id=216) |
| ❌ | `fut_weekly_monthly` | 期货周/月线行情(每日更新) | [337](https://tushare.pro/document/2?doc_id=337) |
| ❌ | `fut_wsr` | 仓单日报 | [140](https://tushare.pro/document/2?doc_id=140) |
| ❌ | `rt_fut_min` | 期货实时分钟行情 | [340](https://tushare.pro/document/2?doc_id=340) |

### option_ 期权（扩展）（✅ 0 · ⚠️ 0 · ❌ 3 / 3）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `opt_basic` | 期权合约信息 | [158](https://tushare.pro/document/2?doc_id=158) |
| ❌ | `opt_daily` | 期权日线行情 | [159](https://tushare.pro/document/2?doc_id=159) |
| ❌ | `opt_mins` | 期权历史分钟行情 | [341](https://tushare.pro/document/2?doc_id=341) |

### hk_ 港股（扩展）（✅ 0 · ⚠️ 0 · ❌ 12 / 12）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `ggt_daily` | 港股通每日成交统计 | [196](https://tushare.pro/document/2?doc_id=196) |
| ❌ | `ggt_top10` | 港股通十大成交股 | [49](https://tushare.pro/document/2?doc_id=49) |
| ❌ | `hk_adjfactor` | 港股复权因子 | [401](https://tushare.pro/document/2?doc_id=401) |
| ❌ | `hk_balancesheet` | 港股资产负债表 | [390](https://tushare.pro/document/2?doc_id=390) |
| ❌ | `hk_basic` | 港股列表 | [191](https://tushare.pro/document/2?doc_id=191) |
| ❌ | `hk_cashflow` | 港股现金流量表 | [391](https://tushare.pro/document/2?doc_id=391) |
| ❌ | `hk_daily` | 港股行情 | [192](https://tushare.pro/document/2?doc_id=192) |
| ❌ | `hk_daily_adj` | 港股复权行情 | [339](https://tushare.pro/document/2?doc_id=339) |
| ❌ | `hk_fina_indicator` | 港股财务指标数据 | [388](https://tushare.pro/document/2?doc_id=388) |
| ❌ | `hk_hold` | 沪深港股通持股明细 | [188](https://tushare.pro/document/2?doc_id=188) |
| ❌ | `hk_income` | 港股利润表 | [389](https://tushare.pro/document/2?doc_id=389) |
| ❌ | `hk_mins` | 港股分钟行情 | [304](https://tushare.pro/document/2?doc_id=304) |

### us_ 美股（扩展）（✅ 0 · ⚠️ 0 · ❌ 13 / 13）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `us_adjfactor` | 美股复权因子 | [402](https://tushare.pro/document/2?doc_id=402) |
| ❌ | `us_balancesheet` | 美股资产负债表 | [395](https://tushare.pro/document/2?doc_id=395) |
| ❌ | `us_basic` | 美股列表 | [252](https://tushare.pro/document/2?doc_id=252) |
| ❌ | `us_cashflow` | 美股现金流量表 | [396](https://tushare.pro/document/2?doc_id=396) |
| ❌ | `us_daily` | 美股行情 | [254](https://tushare.pro/document/2?doc_id=254) |
| ❌ | `us_daily_adj` | 美股复权行情 | [338](https://tushare.pro/document/2?doc_id=338) |
| ❌ | `us_fina_indicator` | 美股财务指标数据 | [393](https://tushare.pro/document/2?doc_id=393) |
| ❌ | `us_income` | 美股利润表 | [394](https://tushare.pro/document/2?doc_id=394) |
| ❌ | `us_tbr` | 短期国债利率 | [221](https://tushare.pro/document/2?doc_id=221) |
| ❌ | `us_tltr` | 国债长期利率 | [222](https://tushare.pro/document/2?doc_id=222) |
| ❌ | `us_trltr` | 国债实际长期利率平均值 | [223](https://tushare.pro/document/2?doc_id=223) |
| ❌ | `us_trycr` | 国债实际收益率曲线利率 | [220](https://tushare.pro/document/2?doc_id=220) |
| ❌ | `us_tycr` | 国债收益率曲线利率（日频） | [219](https://tushare.pro/document/2?doc_id=219) |

### macro_ 宏观（扩展）（✅ 0 · ⚠️ 0 · ❌ 12 / 12）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `cn_cpi` | 居民消费价格指数 | [228](https://tushare.pro/document/2?doc_id=228) |
| ❌ | `cn_gdp` | GDP数据 | [227](https://tushare.pro/document/2?doc_id=227) |
| ❌ | `cn_m` | 货币供应量 | [242](https://tushare.pro/document/2?doc_id=242) |
| ❌ | `cn_pmi` | 采购经理人指数 | [325](https://tushare.pro/document/2?doc_id=325) |
| ❌ | `cn_ppi` | 工业生产者出厂价格指数 | [245](https://tushare.pro/document/2?doc_id=245) |
| ❌ | `cn_schedule` | 中国经济数据发布日程 | [461](https://tushare.pro/document/2?doc_id=461) |
| ❌ | `eco_cal` | 财经日历 | [233](https://tushare.pro/document/2?doc_id=233) |
| ❌ | `hibor` | Hibor利率 | [153](https://tushare.pro/document/2?doc_id=153) |
| ❌ | `libor` | Libor拆借利率 | [152](https://tushare.pro/document/2?doc_id=152) |
| ❌ | `monetary_policy` | 央行货币政策执行报告 | [465](https://tushare.pro/document/2?doc_id=465) |
| ❌ | `sf_month` | 社融数据（月度） | [310](https://tushare.pro/document/2?doc_id=310) |
| ❌ | `shibor` | Shibor利率数据 | [149](https://tushare.pro/document/2?doc_id=149) |

### other_ 其它（✅ 0 · ⚠️ 0 · ❌ 47 / 47）

| 状态 | API | 标题 | doc_id |
|------|-----|------|--------|
| ❌ | `(文档无 api_name)` | 通用行情接口 | [109](https://tushare.pro/document/2?doc_id=109) |
| ❌ | `(文档无 api_name)` | Tushare数据索引 | [209](https://tushare.pro/document/2?doc_id=209) |
| ❌ | `anns_d` | 上市公司全量公告 | [176](https://tushare.pro/document/2?doc_id=176) |
| ❌ | `bc_bestotcqt` | 柜台流通式债券最优报价 | [323](https://tushare.pro/document/2?doc_id=323) |
| ❌ | `bc_otcqt` | 柜台流通式债券报价 | [322](https://tushare.pro/document/2?doc_id=322) |
| ❌ | `bond_blk` | 债券大宗交易 | [271](https://tushare.pro/document/2?doc_id=271) |
| ❌ | `bond_blk_detail` | 大宗交易明细 | [272](https://tushare.pro/document/2?doc_id=272) |
| ❌ | `bse_mapping` | 北交所新旧代码对照表 | [375](https://tushare.pro/document/2?doc_id=375) |
| ❌ | `ccass_hold` | 中央结算系统持股汇总 | [295](https://tushare.pro/document/2?doc_id=295) |
| ❌ | `ccass_hold_detail` | 中央结算系统持股明细 | [274](https://tushare.pro/document/2?doc_id=274) |
| ❌ | `cctv_news` | 新闻联播 | [154](https://tushare.pro/document/2?doc_id=154) |
| ❌ | `ci_index_member` | 中信行业成分 | [373](https://tushare.pro/document/2?doc_id=373) |
| ❌ | `etf_sh_cons` | 每日持仓组合(沪市） | [471](https://tushare.pro/document/2?doc_id=471) |
| ❌ | `fx_obasic` | 外汇基础信息（海外） | [178](https://tushare.pro/document/2?doc_id=178) |
| ❌ | `gz_index` | 广州民间借贷利率 | [174](https://tushare.pro/document/2?doc_id=174) |
| ❌ | `hm_detail` | 游资每日明细 | [312](https://tushare.pro/document/2?doc_id=312) |
| ❌ | `hm_list` | 游资名录 | [311](https://tushare.pro/document/2?doc_id=311) |
| ❌ | `idx_anns` | 指数公司公告 | [460](https://tushare.pro/document/2?doc_id=460) |
| ❌ | `irm_qa_sh` | 上证E互动 | [366](https://tushare.pro/document/2?doc_id=366) |
| ❌ | `irm_qa_sz` | 深证互动易 | [367](https://tushare.pro/document/2?doc_id=367) |
| ❌ | `kpl_concept_cons` | 开盘啦题材成分 | [351](https://tushare.pro/document/2?doc_id=351) |
| ❌ | `kpl_list` | 开盘啦榜单数据 | [347](https://tushare.pro/document/2?doc_id=347) |
| ❌ | `limit_step` | 连板天梯 | [356](https://tushare.pro/document/2?doc_id=356) |
| ❌ | `major_news` | 新闻通讯 | [195](https://tushare.pro/document/2?doc_id=195) |
| ❌ | `news` | 新闻快讯 | [143](https://tushare.pro/document/2?doc_id=143) |
| ❌ | `npr` | 国家政策库 | [406](https://tushare.pro/document/2?doc_id=406) |
| ❌ | `research_report` | 券商研究报告 | [415](https://tushare.pro/document/2?doc_id=415) |
| ❌ | `sge_basic` | 黄金现货基础信息 | [284](https://tushare.pro/document/2?doc_id=284) |
| ❌ | `shibor_lpr` | LPR贷款基础利率 | [151](https://tushare.pro/document/2?doc_id=151) |
| ❌ | `shibor_quote` | Shibor报价数据 | [150](https://tushare.pro/document/2?doc_id=150) |
| ❌ | `slb_len` | 转融资交易汇总 | [331](https://tushare.pro/document/2?doc_id=331) |
| ❌ | `slb_len_mm` | 做市借券交易汇总 | [334](https://tushare.pro/document/2?doc_id=334) |
| ❌ | `slb_sec` | 转融券交易汇总 | [332](https://tushare.pro/document/2?doc_id=332) |
| ❌ | `slb_sec_detail` | 转融券交易明细 | [333](https://tushare.pro/document/2?doc_id=333) |
| ❌ | `st` | ST风险警示板股票 | [423](https://tushare.pro/document/2?doc_id=423) |
| ❌ | `stk_account` | 股票账户开户数据 | [164](https://tushare.pro/document/2?doc_id=164) |
| ❌ | `stk_account_old` | 股票账户开户数据（旧） | [165](https://tushare.pro/document/2?doc_id=165) |
| ❌ | `stk_ah_comparison` | AH股比价 | [399](https://tushare.pro/document/2?doc_id=399) |
| ❌ | `stk_alert` | 交易所重点提示证券 | [453](https://tushare.pro/document/2?doc_id=453) |
| ❌ | `stk_high_shock` | 个股严重异常波动 | [452](https://tushare.pro/document/2?doc_id=452) |
| ❌ | `stk_holdertrade` | 股东增减持 | [175](https://tushare.pro/document/2?doc_id=175) |
| ❌ | `stk_managers` | 上市公司管理层 | [193](https://tushare.pro/document/2?doc_id=193) |
| ❌ | `stk_nineturn` | 神奇九转指标 | [364](https://tushare.pro/document/2?doc_id=364) |
| ❌ | `stk_rewards` | 管理层薪酬和持股 | [194](https://tushare.pro/document/2?doc_id=194) |
| ❌ | `stk_shock` | 个股异常波动 | [451](https://tushare.pro/document/2?doc_id=451) |
| ❌ | `wz_index` | 温州民间借贷利率 | [173](https://tushare.pro/document/2?doc_id=173) |
| ❌ | `yc_cb` | 国债收益率曲线 | [201](https://tushare.pro/document/2?doc_id=201) |

---

## 5. 维护约定

1. **新增 ETL 数据源**：按 [`vibe_tushare_fullstack`](../.claude/skills/vibe_tushare_fullstack/skill.md) 走全链路；同步更新本文件 §2 + [`开发进度.md`](开发进度.md) + `completeness_dashboard_config.py`
2. **更新 Tushare 文档索引**：`uv run python .claude/skills/get_tushare_doc/tushare_doc.py crawl --force`（约 6 分钟）
3. **计数口径**：以「Quantus 语义化数据源 / DB 表」为主键，API 粒度为辅；VIP 与 by-code 变体算同一管线
4. **非 Tushare**：日 K 可降级 `tdx_quant`（本地通达信）；仓库层 `warehouse_` 为 PG→Parquet，不计入 Tushare 接入数
