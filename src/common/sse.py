"""SSE + 后台线程的通用工具。

围绕"daemon worker 把进度入队 + 异步路由非阻塞消费队列"这一固定模式做抽象，
避免每个 SSE 接口重复线程/队列/轮询/yield 模板代码。

关键点：
- 队列消费使用 ``queue.get_nowait()`` + ``asyncio.sleep`` 异步轮询，**禁止** 使用
  ``await asyncio.to_thread(q.get)``。后者在客户端断连时阻塞无法取消，会长期占用默认
  ``ThreadPoolExecutor`` 的工作线程，几个请求后其它接口的 ``to_thread`` 全部饿死。
- ``thread.join`` 同理，统一在 ``finally`` 里以 ``asyncio.sleep`` 轮询 ``is_alive()``。
- worker 线程内的异常会被捕获并以 ``{"error": "..."}`` 入队，路由侧收到后正常结束流。
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Any, AsyncIterator, Callable, Mapping

from fastapi.responses import StreamingResponse

SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    # 关闭 Nginx 等代理的输出缓冲，避免首帧被吞掉。
    "X-Accel-Buffering": "no",
}

_DEFAULT_STARTED_FRAME: Mapping[str, Any] = {"status": "started"}


def _dump_sse(item: Mapping[str, Any]) -> str:
    return f"data: {json.dumps(item, ensure_ascii=False)}\n\n"


async def sse_event_stream(
    worker: Callable[[queue.Queue], None],
    *,
    started_frame: Mapping[str, Any] | None = _DEFAULT_STARTED_FRAME,
    poll_interval: float = 0.02,
    join_interval: float = 0.05,
    thread_name: str | None = None,
) -> AsyncIterator[str]:
    """运行 ``worker(progress_queue)`` 于后台 daemon 线程，把队列内容产为 SSE 帧。

    参数:
        worker: 接收一个 ``queue.Queue`` 的可调用对象，内部把进度/结果/错误 ``put`` 进队列。
            约定结束条件：队列中出现 ``{"done": True, ...}`` 或 ``{"error": ...}`` 帧。
        started_frame: 主协程在启动 worker 前先推一个"已开始"帧给客户端，
            让代理与浏览器尽快建立连接；传 ``None`` 可关闭。
        poll_interval: 队列空时的异步休眠间隔（秒）。
        join_interval: 流结束后等待 worker 线程退出的轮询间隔（秒）。
        thread_name: 可选线程名，便于排查。

    产出: ``"data: <json>\\n\\n"`` 字符串。
    """

    q: queue.Queue = queue.Queue()

    def _runner() -> None:
        try:
            worker(q)
        except Exception as e:  # noqa: BLE001 - 兜底转为错误帧
            q.put({"error": str(e)})

    thread = threading.Thread(target=_runner, daemon=True, name=thread_name)

    if started_frame is not None:
        yield _dump_sse(started_frame)

    thread.start()
    try:
        while True:
            try:
                item: dict = q.get_nowait()
            except queue.Empty:
                if not thread.is_alive():
                    yield _dump_sse({"error": "任务线程已结束但未收到结束帧"})
                    break
                await asyncio.sleep(poll_interval)
                continue
            yield _dump_sse(item)
            if item.get("done") or item.get("error"):
                break
    finally:
        # 不使用 await asyncio.to_thread(thread.join)：阻塞读不可取消，会长期占用线程池。
        while thread.is_alive():
            await asyncio.sleep(join_interval)


def sse_streaming_response(
    task: Callable[..., None],
    /,
    *args: Any,
    progress_queue_kwarg: str = "progress_queue",
    started_frame: Mapping[str, Any] | None = _DEFAULT_STARTED_FRAME,
    thread_name: str | None = None,
    **kwargs: Any,
) -> StreamingResponse:
    """把"约定向 ``progress_queue`` 推帧的同步任务"包装为 SSE ``StreamingResponse``。

    适配条件: ``task(*args, progress_queue=q, **kwargs)`` 内部按需 put：
    ``{"status": "running", "total": N}`` / 每期进度 / ``{"done": True, ...}``。
    异常会被外层捕获转成 ``{"error": str(e)}`` 帧。

    用法::

        return sse_streaming_response(
            strategy.report_income_history_init,
            start_date,
        )
    """

    def _worker(q: queue.Queue) -> None:
        task(*args, **{progress_queue_kwarg: q}, **kwargs)

    return StreamingResponse(
        sse_event_stream(
            _worker,
            started_frame=started_frame,
            thread_name=thread_name,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
