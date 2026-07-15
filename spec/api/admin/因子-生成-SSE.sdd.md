# SDD · 因子生成 SSE

> **HTTP：** `POST /api/admin/etl/sse/run`  
> **task_key：** `factor_compute`  
> **源码：** `src/service/etl/etl_sse_registry.py`、`src/api/routers/admin/etl_sse.py`

---

## 1. 请求体（在通用 SSE body 上扩展）

| 字段 | 说明 |
|------|------|
| task_key | `factor_compute` |
| start_date / end_date | YYYYMMDD；内部转月份 |
| factor_name | 必填，单个因子 |
| force | 可选，默认 false；true 则覆盖已有月份分区 |

---

## 2. 分发

按 `factor_meta.impl_kind`（或因子名推断）：

| impl_kind | 行为 |
|-----------|------|
| `python` / 自研 registry | `FactorComputeStrategy.compute_factor` |
| `formula` 且名 `gtja_alphaN` | `Gtja191Strategy` 单 alpha 或等价按名计算 |
| `tushare` | 返回错误，提示走 Research CLI |

结束后 `FactorMetaService.update_meta()`（失败只打 log）。

---

## 3. 进度

复用现有 SSE 帧：`running` / `done`；Strategy 侧尽量 `progress_queue.put`。
