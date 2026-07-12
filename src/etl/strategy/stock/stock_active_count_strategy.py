from __future__ import annotations

from datetime import datetime

from src.common.setting import settings
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.stock.stock_active_count_workflow import StockActiveCountWorkflow


class StockActiveCountStrategy:
    def __init__(self) -> None:
        self.workflow = StockActiveCountWorkflow()
        self.trade_cal_strategy = TradeCalStrategy()

    def refresh_active_count(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        start = (start_date or settings.etl_start_date("stock_active_count")).strip()
        end = (end_date or datetime.now().strftime("%Y%m%d")).strip()
        if not start or not end or start > end:
            return 0
        print(f"[活跃股票数] 刷新 {start}~{end} ...")
        self.trade_cal_strategy.ensure_trade_cal(
            start_date=start, end_date=end, exchange="SSE",
        )
        n = self.workflow.refresh_active_count(start, end)
        print(f"[活跃股票数] 落库 {n} 条")
        return n
