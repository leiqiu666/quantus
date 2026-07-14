"""把 Strategy 内部 ETL 进度帧翻译成调度命令级 cmd_pct SSE 帧。"""

from __future__ import annotations

import queue
from collections.abc import Callable
from typing import Any

from src.scheduler.cancel import is_cancel_requested


class CommandProgressBridge:
    """Strategy 的 progress_queue 适配器。

    Strategy 常见帧：
      {"status": "running", "total": N}
      {"index": i, "total": N, "period": ..., "saved": ...}
      {"log": "..."}

    翻译为调度 Admin 可读的：
      {"cmd_index", "cmd_total", "cmd_label", "cmd_pct"}
    同百分比只推一次，避免刷屏。

    另提供 ``is_cancelled()``，供 Strategy 在日循环边界检查停止信号。
    """

    def __init__(
        self,
        outer: queue.Queue | None,
        *,
        cmd_index: int,
        cmd_total: int,
        cmd_label: str,
        run_id: int | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        self._outer = outer
        self._cmd_index = cmd_index
        self._cmd_total = cmd_total
        self._cmd_label = cmd_label
        self._last_pct = -1
        if should_cancel is not None:
            self._should_cancel = should_cancel
        elif run_id is not None:
            self._should_cancel = lambda: is_cancel_requested(run_id)
        else:
            self._should_cancel = lambda: False

    def is_cancelled(self) -> bool:
        return bool(self._should_cancel())

    def put(self, item: dict[str, Any]) -> None:
        if self._outer is None or not isinstance(item, dict):
            return

        if "error" in item:
            # 透传错误，由外层收尾
            if self._outer is not None:
                self._outer.put(item)
            return

        if item.get("done") is True:
            # 列级 runner 的 done 由 GapFillRunTracker 统一补发，这里忽略避免双 done
            return

        if isinstance(item.get("log"), str):
            self._outer.put({"log": item["log"]})
            return

        if item.get("status") == "running" and isinstance(item.get("total"), int):
            self._emit_pct(0)
            return

        idx = item.get("index")
        total = item.get("total")
        if isinstance(idx, int) and isinstance(total, int) and total > 0:
            pct = min(100, max(0, int(idx * 100 / total)))
            self._emit_pct(pct)

    def _emit_pct(self, pct: int) -> None:
        if pct == self._last_pct:
            return
        self._last_pct = pct
        self._outer.put({
            "cmd_index": self._cmd_index,
            "cmd_total": self._cmd_total,
            "cmd_label": self._cmd_label,
            "cmd_pct": pct,
        })
