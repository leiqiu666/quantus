"""通用线程池执行器：与 ``create_rate_limiter`` 等多线程安全限流配合使用。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class ThreadPoolRunner:
    """
    在线程池中执行 ``fn(item)``，返回值为**完成顺序**（与 ``items`` 顺序无关）。

    典型用法：``initializer`` 里为当前工作线程创建独立客户端（如 ``KlineExtract()`` / ``ReportExtract()``），
    避免多线程共享非线程安全的 HTTP 客户端；限流仍使用模块级 ``create_rate_limiter`` 即可在进程内共享配额。
    """

    @staticmethod
    def map_unordered(
        items: Sequence[T],
        fn: Callable[[T], R],
        *,
        max_workers: int,
        initializer: Optional[Callable[..., None]] = None,
        initargs: Tuple[Any, ...] = (),
        desc: str = "",
        unit: str = "item",
        on_each_done: Optional[Callable[[R, Any], None]] = None,
    ) -> List[R]:
        item_list = list(items)
        if not item_list:
            return []
        workers = max(1, max_workers)
        results: List[R] = []
        from tqdm.auto import tqdm

        with ThreadPoolExecutor(
            max_workers=workers,
            initializer=initializer,
            initargs=initargs,
        ) as executor:
            future_map = {executor.submit(fn, x): x for x in item_list}
            with tqdm(
                total=len(future_map),
                desc=desc,
                unit=unit,
                mininterval=0.5,
                leave=True,
                dynamic_ncols=True,
            ) as pbar:
                for fut in as_completed(future_map):
                    r = fut.result()
                    results.append(r)
                    if on_each_done is not None:
                        on_each_done(r, pbar)
                    pbar.update(1)
        return results
