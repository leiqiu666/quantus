"""进程内取消信号：Admin 停止执行中的调度 run。"""

from __future__ import annotations

import threading
from typing import Any


class CommandCancelled(Exception):
    """调度命令在执行中被用户停止。"""


_cancel_events: dict[int, threading.Event] = {}
_lock = threading.Lock()


def register_run(run_id: int) -> threading.Event:
    event = threading.Event()
    with _lock:
        _cancel_events[run_id] = event
    return event


def unregister_run(run_id: int) -> None:
    with _lock:
        _cancel_events.pop(run_id, None)


def request_cancel(run_id: int) -> bool:
    """请求取消；返回是否命中本进程内正在跑的 run。"""
    with _lock:
        event = _cancel_events.get(run_id)
    if event is None:
        return False
    event.set()
    return True


def is_cancel_requested(run_id: int) -> bool:
    with _lock:
        event = _cancel_events.get(run_id)
    return bool(event and event.is_set())


def raise_if_progress_cancelled(progress_queue: Any) -> None:
    """Strategy 循环内调用：若 progress_queue 带取消信号则抛 CommandCancelled。"""
    checker = getattr(progress_queue, "is_cancelled", None)
    if callable(checker) and checker():
        raise CommandCancelled("用户停止")
