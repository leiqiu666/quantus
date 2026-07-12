# SDD · ETL 补位 SSE

> **模式：** ② ETL Strategy + SSE  
> **HTTP：** `POST /api/admin/etl/sse/run`  
> **源码：** [`src/api/routers/admin/etl_sse.py`](../../src/api/routers/admin/etl_sse.py)

---

## 1. 概述

通用 ETL 补位入口：`task_key` 映射到 Strategy 方法（`check_complete` / `pull` / `report_history_init`）。

任务注册表：[`src/service/etl/etl_sse_registry.py`](../../src/service/etl/etl_sse_registry.py)

与看板列 `sse_task_key` 一一对应，定义于 [`completeness_dashboard_config.py`](../../src/service/etl/completeness_dashboard_config.py)。

### 触发示例

```bash
curl -N -X POST http://localhost:8000/api/admin/etl/sse/run \
  -H "Content-Type: application/json" \
  -d '{"task_key":"market_moneyflow_check","start_date":"20260629","end_date":"20260703"}'
```

---

## 2. 请求

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_key` | string | SSE 任务键 |
| `start_date` | string | 起始 YYYYMMDD |
| `end_date` | string \| null | 结束 YYYYMMDD；report history init 可省略 |

---

## 3. SSE 帧

| 帧 | 说明 |
|----|------|
| `{"status":"started"}` | 连接建立 |
| `{"status":"running","total":1}` | 任务开始 |
| `{"done":true,"saved":N,"message":"..."}` | 成功结束 |
| `{"error":"..."}` | 失败 |

财报 VIP 全量入库仍走 [`财报-三表历史入库-SSE.sdd.md`](./财报-三表历史入库-SSE.sdd.md) 专用端点（带逐期 progress 帧）。

---

## 4. task_key 与 Strategy

| task_key | Strategy 方法 |
|----------|---------------|
| `report_*_history_init` | `ReportStrategy.report_*_history_init` |
| `market_*_check` | 各 Market Strategy `.check_complete` |
| `financial_*_check` | 各 Financial Strategy `.check_complete` |
| `kline_*_check` | `KlineStrategy.pull_*_by_date_range` 或 `check_kline_complete_history` |
| `stock_suspend_pull` | `SuspendStrategy.pull_suspend_by_date` |
| `index_weight_check` | `IndexWeightStrategy.check_complete` |

完整列表以代码注册表为准。
