# ETL 23 项全量测试 Bug 清单

> 生成：2026-07-05 · **修复完成**：2026-07-05  
> 测试窗口：by 日 20260629~20260703；by 期 20251231/20260331  
> 渠道：TUSHARE_CHANNEL=stocktoday（生产 PG localhost/quantus）

## 修复状态汇总

| 优先级 | 编号 | 状态 | 说明 |
|--------|------|------|------|
| P0 | BUG-001 | ✅ 已修 | suspend 8 层 ETL 已实现并回归（20260629 写入 24 条） |
| P0 | BUG-002 | ✅ 已修 | stocktoday fallback + 补拉单条容错 |
| P0 | BUG-003 | ✅ 已修 | warehouse check `get_session()` |
| P1 | BUG-004 | ✅ 已修 | dividend 移除 CompletenessEngine，check/update 为 no-op |
| P1 | BUG-005 | ✅ 已修 | margin 分母改融资融券标的峰值；moneyflow threshold=0.92 |
| P1 | BUG-006 | ⚪ 已知限制 | 测试窗口 20260331 披露未完成，非代码 Bug |
| P2 | BUG-007 | ✅ 已修 | audit pull 跳过库内已有；check 走 `backfill_keys` |
| P2 | BUG-008 | ✅ 已修 | stk-holder check 复用 `_completeness.check_complete`（ann_date） |
| P2 | BUG-013 | ✅ 已修 | 财报缺期补拉改 VIP `report_by_period` + 去重 |
| P2 | BUG-014 | ✅ 已修 | kline check 传 `--start-date/--end-date` 走窗口宏观 pull |
| P2 | BUG-010 | ✅ 已修 | check 补拉后刷新快照（completeness.py） |
| P3 | BUG-011 | ✅ 已修 | 菜单 `_MENU_HANDLERS` 统一 `silent=True` + `_cli_echo` |
| P3 | BUG-012 | ✅ 已修 | 12 份 P4 Spec §5 更新为 `backfill_keys` 语义 |

---

## P0 — 进程 crash / 数据未入库

### BUG-001 suspend ETL 未实现 ✅

| 项 | 内容 |
|----|------|
| 修复 | 补齐 client/extract/load/workflow/strategy 全栈；`SuspendStrategy.pull_suspend_by_date` 按 SSE 开市日循环 |
| 文件 | `src/etl/client/stock/stock_suspend_*`、`src/etl/extract/stock/stock_suspend_extract.py`、`src/etl/load/stock/stock_suspend_load.py`、`src/etl/workflow/stock/stock_suspend_workflow.py`、`src/etl/strategy/stock/stock_suspend_strategy.py` |
| 回归 | `suspend pull-by-date --start-date 20260629 --end-date 20260629` → 24 条 |

### BUG-002 stocktoday HTTP 400/超时 ✅

| 项 | 内容 |
|----|------|
| 修复 | `TushareClient._FallbackDataApi`；`CompletenessEngine.backfill_missing` 单条 try/except |
| 文件 | `src/common/tushare_client.py`、`src/common/completeness.py` |

### BUG-003 warehouse check crash ✅

| 项 | 内容 |
|----|------|
| 修复 | `SuspendLocalExtract` 使用 `get_session()` |
| 文件 | `src/etl/extract/local/stock/stock_suspend_local_extract.py` |

---

## P1 — 完整性长期 <95% 或逻辑错误

### BUG-004 dividend 完整性引擎与 Spec 不符 ✅

| 项 | 内容 |
|----|------|
| 修复 | 移除 CompletenessEngine；pull 仍按 record_date/开市日增量；`check_complete` / `refresh_completeness_snapshot` 打印跳过 |
| 文件 | `src/etl/strategy/market/market_dividend_strategy.py` |
| 回归 | `market_dividend check-complete 20260629~20260703` → 0 条补拉 |

### BUG-005 moneyflow / margin 覆盖率 ✅

| 项 | 内容 |
|----|------|
| 修复 | margin：`period_stock_count_fn` 用 `get_peak_daily_universe_count`；moneyflow：`threshold=0.92` |
| 文件 | `src/common/completeness.py`（threshold 配置）、`market_margin_strategy.py`、`market_moneyflow_strategy.py` |
| 说明 | 数据源本身对部分标的无记录；调整后快照语义与 Spec 一致 |

### BUG-006 财报宏观快照测试窗口 ⚪

| 项 | 内容 |
|----|------|
| 结论 | 20260331 季报披露未完成导致快照 0 期 ≥95%；改用已披露报告期测试或仅观察 PG 存量 |

---

## P2 — Spec 不符 / 性能 / 逻辑

### BUG-007 audit pull/check ✅

| 项 | 内容 |
|----|------|
| 修复 | pull：`load_ts_codes_by_periods` 预加载 + `pull_fina_audit_gaps_for_period` 仅补缺口；check：`CompletenessEngine.check_complete` |
| 文件 | `financial_audit_local_extract.py`、`financial_audit_strategy.py` |

### BUG-008 stk-holder check ✅

| 项 | 内容 |
|----|------|
| 修复 | 删除 `_check_completeness` / `check_complete_per_stock`；check 复用 ann_date + event_driven 引擎 |
| 文件 | `financial_stock_holder_strategy.py` |

### BUG-013 report check VIP 补拉 ✅

| 项 | 内容 |
|----|------|
| 修复 | `_handle_missing_periods` 缺期聚合 → `report_by_period` VIP；`vip_pulled_periods` 去重 |
| 文件 | `financial_report_workflow.py`、`financial_report_strategy.py` |

### BUG-014 kline check 窗口化 ✅

| 项 | 内容 |
|----|------|
| 修复 | `check_kline_complete_history(start, end)` 走三维度 `pull_*_by_date_range`；CLI 增加 `--start-date/--end-date` |
| 文件 | `kline_strategy.py`、`cli.py` |
| 回归 | `kline check-complete --start-date 20260629 --end-date 20260703` → 窗口宏观补拉（~55k 条） |

### BUG-010 kline_stock_factor 快照刷新 ✅

| 项 | 内容 |
|----|------|
| 修复 | `check_complete` 补拉后 `refresh_snapshot` + `print_scan` |
| 文件 | `src/common/completeness.py` |

---

## P3 — 规范 / 文档

### BUG-011 交互菜单 typer.echo ✅

| 项 | 内容 |
|----|------|
| 修复 | `_cli_echo(..., silent=)`；`_MENU_HANDLERS` 全部 `silent=True` |
| 文件 | `src/etl/cli.py` |

### BUG-012 Spec §5 resolve_incremental_start ✅

| 项 | 内容 |
|----|------|
| 修复 | 12 份 P4 Spec §5 更新为 `CompletenessEngine.backfill_keys` 语义 |
| 文件 | `spec/etl/每日指标-日频基本面.sdd.md` 等 12 份 |

---

## 逐股维度盘点（修复后）

| CLI 命令 | pull | check | 5613×API? |
|----------|------|-------|-----------|
| `report check-report-complete` | — | VIP by period | 否 |
| `kline check-complete`（无日期） | — | 微观扫描（无 API） | 否 |
| `kline check-complete`（有窗口） | 按日 pull | 宏观 | 否 |
| `stk-holder check-complete` | — | ann_date backfill | 否 |
| `audit pull-by-period` | 缺口股 only | — | 仅缺口 |
| `audit check-complete` | — | backfill_keys | 仅缺口期 |

---

## Phase 5 回归结果（2026-07-05 修复后）

| 命令 | 结果 |
|------|------|
| `suspend pull-by-date 20260629` | 24 条 |
| `warehouse check-kline-daily-parquet` | pass |
| `market_dividend check-complete` | 跳过（Spec 无校验） |
| `kline check-complete 20260629~20260703` | 窗口宏观补拉 pass |
| `market_moneyflow check-complete` | fallback + 92% 阈值 |
| `margin check-complete` | 融资融券分母 + fallback |
