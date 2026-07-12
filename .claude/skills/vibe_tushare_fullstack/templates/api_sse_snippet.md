# SSE 任务注册片段

> 添加到 [`src/service/etl/etl_sse_registry.py`](../../../src/service/etl/etl_sse_registry.py) 的 `SSE_TASK_REGISTRY`。

## check_complete（最常见 · 推荐）

```python
"{{sse_task_key}}": lambda start, end, q: _run_check(
    {{StrategyClass}}().check_complete, start, end, q,
),
```

Strategy 须转发 `progress_queue`：

```python
def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
    return self._completeness.check_complete(
        start_date, end_date, progress_queue=progress_queue,
    )
```

`_run_check` 会把 `progress_queue` 传给 `check_complete`；`CompletenessEngine` 负责按缺口日/期推帧。**不要**在 registry 里额外 `q.put({"total": 1})`。

需在文件顶部 import Strategy：

```python
from src.etl.strategy.{{domain_dir}}.{{domain}}_strategy import {{StrategyClass}}
```

## pull_by_date 长循环（停复牌 / K 线等）

**禁止**下列写法（前端会卡在「共 1 步」）：

```python
# ❌ 反例
q.put({"status": "running", "total": 1})
saved = Strategy().pull_xxx_by_date(start, end)  # 内部 tqdm，无 SSE 帧
q.put({"done": True, ...})
```

**应该**：Strategy 方法接受 `progress_queue`，循环内推帧：

```python
# Strategy 内
if progress_queue is not None:
    progress_queue.put({"status": "running", "total": len(dates)})
    for i, dk in enumerate(dates, 1):
        saved = self._pull_one(dk)
        progress_queue.put({
            "index": i, "total": len(dates), "period": dk, "saved": saved,
        })
```

Registry 示例：

```python
# 停复牌 — 复用 _run_suspend_pull
"stock_suspend_pull": lambda start, end, q: _run_suspend_pull(start, end, q),

# K 线维度 — 复用 _run_kline_dim
"kline_daily_check": lambda start, end, q: _run_kline_dim("daily", start, end, q),
```

## SSE 帧协议（前端 [`SseTaskManager`](../../../src/web/admin/src/components/SseTask/SseTaskManager.tsx)）

| 帧 | 说明 |
|----|------|
| `{"status": "started"}` | 由 `sse_event_stream` 自动发送 |
| `{"log": "..."}` | 追加运行日志 |
| `{"status": "running", "total": N}` | 设置总步数 |
| `{"index", "total", "period", "saved"}` | 单步进度 |
| `{"done": true, "message": "...", "saved": N}` | 结束 |

## 前端调用链（已实现，通常无需改）

- Admin：`useSseTask().startEtlTask({ taskKey, label, startDate, endDate })`
- HTTP：`POST /api/admin/etl/sse/run` body `{ task_key, start_date, end_date }`
- 组件：[`DataSourceDashboardTable`](../../../src/web/admin/src/components/DataSourceDashboard/DataSourceDashboardTable.tsx)
- 表头补位区间：看板搜索范围，默认起点来自 API `meta.default_start`（Pydantic `DashboardMeta` 须声明该字段）

## validate_sse_task_key

`task_key` 须在 `all_sse_task_keys()`（来自 dashboard config）或 `SSE_TASK_REGISTRY` 中，否则 API 400。
