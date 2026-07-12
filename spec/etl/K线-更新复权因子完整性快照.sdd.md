# SDD · K 线更新复权因子完整性快照

> **CLI 命令：** `kline update-adj-factor-period-count`  
> **交互菜单：** 【K线】更新复权因子完整性快照  
> **统一快照表：** `kline_daily_period_count`（见 [`K线-更新日线完整性快照.sdd.md`](./K线-更新日线完整性快照.sdd.md)）

---

## 1. 概述

本命令为 **`kline update-daily-period-count` 的别名**：同样刷新 `kline_daily_period_count` 全行（含 `kline_adj_factor_count` 列）。95% 缺失日筛选读取该表的 `kline_adj_factor_count` / `period_stock_count`。

```bash
uv run ./src/etl/cli.py kline update-adj-factor-period-count
```

实现：`KlineStrategy.kline_adj_factor_period_count()` → `kline_daily_period_count()`。
