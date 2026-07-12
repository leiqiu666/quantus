"""国泰 191 因子计算 Strategy：按月编排 + 进度队列。"""

from __future__ import annotations

import math
import queue
from datetime import datetime

from src.common.function import tqdm_iter
from src.research.dataset.kline import KlineDataset
from src.research.factor.gtja.catalog import list_computable_alphas, load_catalog
from src.research.factor.gtja.engine import Gtja191Engine


def _ymd_to_month(ymd: str) -> str:
    return (ymd or "").strip()[:6]


class Gtja191Strategy:
    def __init__(self) -> None:
        self._engine = Gtja191Engine()
        self._kline = KlineDataset()

    def compute(
        self,
        start_month: str | None = None,
        end_month: str | None = None,
        alpha: int | None = None,
        force: bool = False,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        months = self._kline.list_available_months()
        if start_month:
            months = [m for m in months if m >= start_month]
        if end_month:
            months = [m for m in months if m <= end_month]
        if not months:
            msg = "无可用日 K 月份"
            print(msg)
            if progress_queue is not None:
                progress_queue.put({"done": True, "saved": 0, "message": msg})
            return 0

        specs = list_computable_alphas(alpha)
        if alpha is not None and not specs:
            cat = load_catalog()[alpha]
            msg = f"{cat.name} 跳过计算: {cat.skip_reason}"
            print(msg)
            if progress_queue is not None:
                progress_queue.put({"done": True, "saved": 0, "message": msg})
            return 0

        total_rows = 0
        ok_factors: set[str] = set()
        n_months = len(months)
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": n_months})

        for i, ym in enumerate(tqdm_iter(months, desc="国泰191按月计算"), start=1):
            if progress_queue is not None:
                progress_queue.put({"log": f"计算月份 {ym}（{i}/{n_months}）"})
            part = self._engine.compute_month(ym, specs, force=force)
            rows = sum(part.values())
            total_rows += rows
            ok_factors.update(part.keys())
            if progress_queue is not None:
                progress_queue.put({
                    "index": i,
                    "total": n_months,
                    "period": ym,
                    "saved": rows,
                })

        msg = (
            f"国泰191完成：{len(months)} 个月，成功写出 {len(ok_factors)} 个因子，"
            f"累计 {total_rows} 行"
        )
        print(msg)
        if progress_queue is not None:
            progress_queue.put({"done": True, "saved": total_rows, "message": msg})
        return total_rows

    def compute_by_date_range(
        self,
        start_date: str,
        end_date: str,
        force: bool = False,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """SSE 入口：YYYYMMDD → 月份。"""
        sm = _ymd_to_month(start_date)
        em = _ymd_to_month(end_date or datetime.now().strftime("%Y%m%d"))
        return self.compute(
            start_month=sm,
            end_month=em,
            force=force,
            progress_queue=progress_queue,
        )
