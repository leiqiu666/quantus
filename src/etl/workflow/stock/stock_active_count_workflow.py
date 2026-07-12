from __future__ import annotations

from src.common.function import report_period_generate
from src.etl.extract.local.stock.stock_local_extract import StockExtract as LocalStockExtract
from src.etl.extract.local.stock.stock_suspend_local_extract import SuspendLocalExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
    TradeCalLocalExtract,
)
from src.etl.load.stock.stock_active_count_load import StockActiveCountLoad
from src.etl.transform.stock.stock_transform import StockTransform


class StockActiveCountWorkflow:
    def __init__(self) -> None:
        self.local_stock_extract = LocalStockExtract()
        self.trade_cal_local = TradeCalLocalExtract()
        self.suspend_local = SuspendLocalExtract()
        self.stock_transform = StockTransform()
        self.load = StockActiveCountLoad()

    def build_active_count_rows(
        self, start_date: str, end_date: str
    ) -> list[dict[str, int | str | None]]:
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return []

        trade_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=start, end_date=end, exchange="SSE",
        )
        report_periods = report_period_generate(start, end)
        date_keys = sorted(set(trade_dates) | set(report_periods))
        if not date_keys:
            return []

        stock_rows = self.local_stock_extract.get_stock_list()
        suspend_by_code = self.suspend_local.preload_full_day_suspend_dates(
            start_date=start,
            end_date=end,
        )
        return self.stock_transform.build_active_count_rows(
            stock_rows,
            date_keys,
            trade_date_set=set(trade_dates),
            suspend_by_code=suspend_by_code,
        )

    def refresh_active_count(self, start_date: str, end_date: str) -> int:
        rows = self.build_active_count_rows(start_date, end_date)
        if not rows:
            return 0
        return self.load.load_active_count_rows(rows)
