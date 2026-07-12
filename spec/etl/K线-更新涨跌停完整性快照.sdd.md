# SDD · K 线更新涨跌停完整性快照

> **CLI 命令：** `kline update-stk-limit-period-count`  
> **交互菜单：** 【K线】更新涨跌停完整性快照  
> **统一快照表：** `kline_daily_period_count`（见 [`K线-更新日线完整性快照.sdd.md`](./K线-更新日线完整性快照.sdd.md)）

---

## 1. 概述

本命令刷新 **`kline_daily_period_count` 全行**（含 `kline_stk_limit_count` 列）。默认统计起点为 `max(KLINE_DAILY_START_DATE, KLINE_STK_LIMIT_START_DATE)`。

```bash
uv run ./src/etl/cli.py kline update-stk-limit-period-count
```

实现：`KlineStrategy.kline_stk_limit_period_count()` → `kline_daily_period_count(start=...)`。
