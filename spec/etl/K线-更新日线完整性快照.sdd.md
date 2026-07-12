# SDD · K 线更新日 K 完整性快照

> **CLI 命令：** `kline update-daily-period-count`（隐藏别名：`update-adj-factor-period-count`、`update-stk-limit-period-count`）  
> **交互菜单：** 【K线】【宏观】刷新日K完整性快照  
> **源码入口：** [`src/etl/cli.py`](../../src/etl/cli.py)

---

## 1. 概述

刷新 **`kline_daily_period_count` 唯一快照表**：对每个 SSE 开市日记录

| 字段 | 含义 |
|------|------|
| `period_stock_count` | 该日应在市股票数 |
| `kline_daily_count` | 已入库日线条数 |
| `kline_adj_factor_count` | `kline_daily.adj_factor` 非空条数 |
| `kline_stk_limit_count` | `up_limit`、`down_limit` 均非空条数 |

供 `pull-daily-by-date-range` / `pull-adj-factor-by-date-range` / `pull-stk-limit-by-date-range` 的 **95% 缺失日筛选**，以及微观完整性检查的宏观截止日判定。**不调用远程 K 线 API**，纯本地读库聚合。

**宏观进度：** Strategy 层 `refresh_kline_macro_snapshot()` 打印 `[宏观] 刷新...` 与耗时；pull 结束后的 `finalize_*_after_update()` 亦仅调用此方法。

### 触发方式

```bash
uv run ./src/etl/cli.py kline update-daily-period-count
# 以下 hidden 别名，行为完全相同：
uv run ./src/etl/cli.py kline update-adj-factor-period-count
uv run ./src/etl/cli.py kline update-stk-limit-period-count
```

### 前置依赖

| 依赖 | 说明 |
|------|------|
| `stock_list` | 计算各日应在市股数 |
| `stock_trade_calendar` | SSE 开市日列表 |
| `kline_daily` | 聚合 daily / adj_factor / stk_limit 各日条数 |
| `KLINE_DAILY_START_DATE` | 默认 `--start-date` |

---

## 3. 分层架构

```
CLI → KlineStrategy.kline_daily_period_count
  ensure_trade_cal(SSE)
  KlineWorkflow.kline_daily_period_count
    1. LocalStockExtract.get_stock_list()
    2. TradeCalLocalExtract.get_open_trade_dates()
    3. KlineDailyService 聚合 daily / adj_factor / stk_limit count
    4. StockTransform.trade_date_stock_count()
    5. KlineLoad.load_kline_daily_period_count()
```

---

## 5. 逐步说明

| 步骤 | 处理 |
|------|------|
| 1 | 解析区间，无效 return 0 |
| 2 | `ensure_trade_cal(SSE)` |
| 3 | 读 `stock_list`、SSE 开市日 |
| 4 | 从 `kline_daily` 聚合各维度条数 |
| 5 | merge 后 upsert `kline_daily_period_count`（冲突键 `trade_date`） |

**写入字段：** `trade_date`, `period_stock_count`, `kline_daily_count`, `kline_adj_factor_count`, `kline_stk_limit_count`

---

## 6. 相关命令

| 命令 | 关系 |
|------|------|
| `kline pull-daily-by-date-range` | 读 `kline_daily_count` 筛缺失日 |
| `kline pull-adj-factor-by-date-range` | 读 `kline_adj_factor_count` 筛缺失日 |
| `kline pull-stk-limit-by-date-range` | 读 `kline_stk_limit_count` 筛缺失日 |
| `kline check-*-complete` | 任务前后刷新本表 |
| `stock pull-list-a` + `report update-period-count` | 刷新本表（不跑微观检查） |

---

## 附录 · Call Stack

```
_run_kline_update_daily_period_count()
└─ KlineStrategy.kline_daily_period_count()
   ├─ ensure_trade_cal()
   └─ KlineWorkflow.kline_daily_period_count()
      ├─ list_trade_date_kline_counts → kline_daily
      ├─ list_trade_date_adj_factor_counts → kline_daily.adj_factor
      ├─ list_trade_date_stk_limit_counts → kline_daily up/down
      ├─ trade_date_stock_count()
      └─ load_kline_daily_period_count() → kline_daily_period_count
```
