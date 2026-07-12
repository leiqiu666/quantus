# ETL 23 项菜单测试 Runbook

> 生成时间：2026-07-05  
> 测试库：localhost / quantus（生产 PG）  
> Tushare 渠道：stocktoday  

## Phase 0 — 测试基线

### 窗口参数

| 参数 | 值 |
|------|-----|
| 今日 | 20260705 |
| 最近 5 SSE 开市日 | 20260629, 20260630, 20260701, 20260702, 20260703 |
| D5（起点） | 20260629 |
| D1（终点） | 20260703 |
| 测试月 YYYYMM | 202606 |
| 报告期 | 20251231, 20260331 |

### 环境

| 项 | 值 |
|----|-----|
| TUSHARE_CHANNEL | stocktoday |
| 多数表 START_DATE | 20260101 |
| stock_suspend START_DATE | 19900101 |

辅助脚本：`scripts/etl_audit/`（resolve_test_dates / snapshot_status / table_baseline / sample_semantic）

### 23 项映射表

| # | menu_key | CLI 命令 | Strategy | PG 表 | completeness source | Spec |
|---|----------|----------|----------|-------|---------------------|------|
| 1 | report-history-init | report report-history-init | financial_report_strategy | financial_report_* ×4 | financial_report_period_count | spec/etl/财报-三表全量历史入库.sdd.md |
| 2 | stock-pull-list-a | stock pull-list-a | stock_strategy | stock_list | — | spec/etl/基础-A股股票列表拉取.sdd.md |
| 3 | trade-cal-pull-history | trade-cal pull-history | stock_trade_calendar_strategy | stock_trade_calendar | — | spec/etl/基础-交易日历增量入库.sdd.md |
| 4 | suspend-pull-by-date | suspend pull-by-date | stock_suspend_strategy | stock_suspend | — | spec/etl/基础-A股停复牌数据入库.sdd.md |
| 5 | kline-pull-daily-by-date-range | kline pull-daily-by-date-range | kline_strategy | kline_daily | kline_daily_period_count | spec/etl/K线-按date区间增量.sdd.md |
| 6 | kline-pull-adj-factor-by-date-range | kline pull-adj-factor-by-date-range | kline_strategy | kline_daily | kline_daily_period_count | 同上 |
| 7 | kline-pull-stk-limit-by-date-range | kline pull-stk-limit-by-date-range | kline_strategy | kline_daily | kline_daily_period_count | 同上 |
| 8 | daily-basic-pull-by-date-range | daily-basic pull-by-date-range | market_daily_basic_strategy | market_daily_basic | market_daily_basic | spec/etl/每日指标-日频基本面.sdd.md |
| 9 | dividend-pull-by-date-range | market_dividend pull-by-date-range | market_dividend_strategy | market_dividend | market_dividend | spec/etl/分红送股.sdd.md |
| 10 | stk-factor-pull-by-date-range | stk-factor pull-by-date-range | kline_stock_factor_strategy | kline_stock_factor | kline_stock_factor | spec/etl/技术面因子.sdd.md |
| 11 | moneyflow-pull-by-date-range | market_moneyflow pull-by-date-range | market_moneyflow_strategy | market_moneyflow | market_moneyflow | spec/etl/资金流向-个股.sdd.md |
| 12 | margin-pull-detail-by-date-range | margin pull-detail-by-date-range | market_margin_strategy | market_margin_detail | market_margin_detail | spec/etl/融资融券-明细.sdd.md |
| 13 | hsgt-pull-top10-by-date-range | hsgt pull-top10-by-date-range | market_northbound_strategy | market_northbound_top10 | market_northbound_top10 | spec/etl/沪深港通-十大成交股.sdd.md |
| 14 | stk-holder-pull-number | stk-holder pull-number | financial_stock_holder_strategy | financial_stock_holder | financial_stock_holder | spec/etl/股东户数.sdd.md |
| 15 | index-pull-weight-by-month-range | index pull-weight-by-month-range | index_weight_strategy | index_weight | index_weight | spec/etl/指数成分权重.sdd.md |
| 16 | dragon-tiger-pull-by-date-range | dragon-tiger pull-by-date-range | market_dragon_tiger_strategy | market_dragon_tiger_list+inst | dragon_tiger | spec/etl/龙虎榜.sdd.md |
| 17 | block-trade-pull-by-date-range | block-trade pull-by-date-range | market_block_trade_strategy | market_block_trade | market_block_trade | spec/etl/大宗交易.sdd.md |
| 18 | shareholder-pull-by-date | shareholder pull-by-date | financial_shareholder_strategy | financial_shareholder_top10 | financial_shareholder_top10 | spec/etl/前十大股东.sdd.md |
| 19 | forecast-pull-by-period | financial_forecast pull-by-period | financial_forecast_strategy | financial_forecast | financial_forecast | spec/etl/业绩预告.sdd.md |
| 20 | express-pull-by-period | financial_express pull-by-period | financial_express_strategy | financial_express | financial_express | spec/etl/业绩快报.sdd.md |
| 21 | audit-pull-by-period | audit pull-by-period | financial_audit_strategy | financial_audit | financial_audit | spec/etl/财务审计意见.sdd.md |
| 22 | warehouse-pull-kline-daily-by-month-range | warehouse pull-kline-daily-by-month-range | warehouse_kline_daily_strategy | Parquet | — | spec/etl/仓库-PG日K导出Parquet.sdd.md |
| 23 | warehouse-check-kline-daily-parquet | warehouse check-kline-daily-parquet | warehouse_kline_daily_strategy | 对账 | — | 同上 |

---

## Phase 1 — 静态 Spec 合规审计

**结论**：22 pass / 1 fail（CLI→Strategy 分层）

| # | 结果 | 主要问题 |
|---|------|----------|
| 1–3, 5–23 | pass | 交互菜单 `_run_*` 路径多数含 typer.echo（违反 CLAUDE 约定，P3） |
| 4 | **fail** | `SuspendStrategy.pull_suspend_by_date` 仍为 TODO，无 Workflow/Extract/Load |
| 9 | pass（疑点） | 曾用 `date_column=end_date`；Spec 声明**不做完整性校验**但代码仍挂 CompletenessEngine（见 BUG-004） |
| 12 项 P4 | pass（Spec 漂移） | Spec §5 仍写 `resolve_incremental_start`，代码已改 `backfill_keys` |
| 逐股维度 | **4 项逻辑 Bug** | 见 [`etl-audit-bugs.md`](etl-audit-bugs.md) BUG-007/008/013/014；其余 23 项 pull/check 均为按日/按期 |

---

## Phase 2 — 基础依赖

| 顺序 | 菜单 | 命令 | 结果 |
|------|------|------|------|
| A | #2 | `stock pull-list-a` | `stock_list` 5940 行 |
| B | #4 | `trade-cal pull-history` | 日历至 20260705，写入 0 |
| C | #3 | `suspend pull-by-date` | **TODO 占位**，返回 0；窗口内 suspend 无增量 |

**Gate 2**：#2/#4 OK；#4 阻塞 K 线全天停牌扣除（见 BUG-001）。

---

## Phase 3 — 运行时测试

### 3A 财报（#1，跳过全量 init）

| 命令 | 结果 |
|------|------|
| `report update-period-count --start-period 20251231 --end-period 20260331` | 成功；宏观快照 0 期 ≥95%（披露未完成） |
| PG 四表 | income/balance/indicator ~29 万行；cashflow ~23 万行 |

### 3B K 线（#5–7，20260629~20260703）

| 维度 | daily | adj_factor | stk_limit |
|------|-------|------------|-----------|
| pull | 27558 | 27659 | 初跑 5491（1/5 日）；回归 27753 |
| kline_daily_period_count | 修复后 **达标** | | |
| 备注 | stk-limit 初跑 stocktoday HTTP 400；Phase 5 fallback 后 5 日齐全 | | |

### 3C 市场/财务 by-date（#8–18）

日志：`/tmp/etl_phase3c.log`

| # | 项 | pull | check | 备注 |
|---|-----|------|-------|------|
| 8 | daily-basic | 跳过 | 达标 | |
| 9 | dividend | 37+8 行 | **仍 5 日缺口** | BUG-004 |
| 10 | stk-factor | 22052 | 20260629 仍 1 缺口 | |
| 11 | moneyflow | 初 **crash** | 初 **crash** | Phase 5 回归 OK ~92% |
| 12 | margin | 初 **crash** | 初 **crash** | Phase 5 回归 OK ~78% |
| 13 | hsgt | OK | OK | |
| 14 | stk-holder | OK | 补拉 52；check **5613 逐股×API ~37min+** | BUG-008：pull 按 ann_date，check 按 ts_code |
| 15 | index | 202606 OK | OK | |
| 16 | dragon-tiger | OK | 补拉 5439 | |
| 17 | block-trade | 334 | 补拉 334 | |
| 18 | shareholder | 0（2 公告日） | 达标 | |

### 3D 预告/快报/审计（#19–21，20251231~20260331）

日志：`/tmp/etl_phase3d.log`

| 项 | pull | check | 快照 |
|----|------|-------|------|
| forecast | OK | 补拉 2721 | **达标** |
| express | OK | 补拉 2324 | **达标** |
| audit | **FAIL** ReadTimeout 中途 | **FAIL** 逐股超时 | 窗口内 **达标**（历史数据）；pull/check 均为 **period×5613 逐股**（BUG-007） |

### 3E 仓库（#22–23）

| 命令 | 初跑 | Phase 5 回归 |
|------|------|--------------|
| `warehouse pull-kline-daily-by-month-range --start-month 202606` | 已存在，0 行 | — |
| `warehouse check-kline-daily-parquet` | **crash** BUG-003 | **pass** |

---

## Phase 4 — Bug 清单

详见 [`docs/etl-audit-bugs.md`](etl-audit-bugs.md)。

---

## Phase 5 — 回归

| 修复项 | 文件 |
|--------|------|
| stocktoday→official fallback | `src/common/tushare_client.py` |
| 补拉单条容错 + 补拉后刷新快照 | `src/common/completeness.py` |
| dividend date_column | `market_dividend_strategy.py` |
| SuspendLocalExtract session | `stock_suspend_local_extract.py` |
| audit 网络重试 | `financial_audit_tushare_client.py` |

回归命令与结果见 `etl-audit-bugs.md` §Phase 5 回归。

**Gate 5 状态**：P0 crash 类已修；suspend 全量 ETL、dividend/margin 完整性语义仍待排期。
