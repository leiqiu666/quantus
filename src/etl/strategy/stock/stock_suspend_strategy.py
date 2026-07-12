"""停复牌 Strategy：区间编排。"""

from __future__ import annotations

import queue
from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.stock.stock_suspend_local_extract import SuspendLocalExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.stock.stock_suspend_workflow import SuspendWorkflow


class SuspendStrategy:
    def __init__(self) -> None:
        self.suspend_workflow = SuspendWorkflow()
        self.suspend_local = SuspendLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.trade_cal_local = TradeCalLocalExtract()
        self.suspend_start_date = settings.etl_start_date("stock_suspend")

    def pull_suspend_by_date(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """按 SSE 开市日逐日拉取 Tushare suspend_d 并 upsert。"""
        if start_date is None:
            start_date = self.suspend_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        eff_start = self.suspend_local.resolve_incremental_start(configured_start=floor)
        if not eff_start or eff_start > end:
            max_td = self.suspend_local.get_max_trade_date()
            msg = f"stock_suspend 已同步至 {max_td or '无'}，跳过"
            if progress_queue is not None:
                progress_queue.put({"log": msg})
            print(f"[信息] {msg}")
            return 0

        open_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=eff_start,
            end_date=end,
            exchange="SSE",
        )
        if not open_dates:
            if progress_queue is not None:
                progress_queue.put({"log": f"{eff_start}~{end} 无 SSE 开市日"})
            print(f"[信息] {eff_start}~{end} 无 SSE 开市日")
            return 0

        print(
            f"[信息] {eff_start}~{end} 共 {len(open_dates)} 个开市日待拉"
            f"（首日 {open_dates[0]}，末日 {open_dates[-1]}）"
        )
        if progress_queue is not None:
            progress_queue.put({"log": f"{len(open_dates)} 个开市日待拉"})
            progress_queue.put({"status": "running", "total": len(open_dates)})

        total_saved = 0
        if progress_queue is not None:
            for i, td in enumerate(open_dates, 1):
                n = self.suspend_workflow.pull_suspend_by_date(td)
                total_saved += n
                progress_queue.put({
                    "index": i,
                    "total": len(open_dates),
                    "period": td,
                    "saved": n,
                })
        else:
            for td in tqdm_iter(open_dates, desc="停复牌入库", unit="日"):
                n = self.suspend_workflow.pull_suspend_by_date(td)
                total_saved += n

        return total_saved
