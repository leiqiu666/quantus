# Quantus Load · SDD 规格文档

本目录存放 **ETL Load 层可复用入库模式** 的运行规格，与 `spec/etl/` 中「整条 CLI 命令」规格互补。

| 文档 | 定位 |
|------|------|
| [`spec/etl/`](../etl/README.md) | 命令级 ETL：Extract → Transform → Load 全链路 |
| `spec/load/*.sdd.md` | Load 模式级：入库策略、比对规则、试点表与接入点 |

## 文档索引

| 文档 | 接入范围 | 源码 |
|------|----------|------|
| [存储-先查再改再插.sdd.md](./存储-先查再改再插.sdd.md) | 财报三表 `by_period` / `by_ts_code`；日 K `pull_kline_daily_by_date` | [`report_load.py`](../../src/etl/load/financial/report_load.py) `load_report_filter`；[`kline_load.py`](../../src/etl/load/kline/kline_load.py) `load_kline_daily_filter` |
