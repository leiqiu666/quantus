"""回测调仓日历。"""

from __future__ import annotations

from datetime import datetime

from src.service.stock.stock_trade_cal_service import TradeCalService


class RebalanceCalendar:
    def __init__(self, exchange: str = "SSE") -> None:
        self._cal = TradeCalService()
        self._exchange = exchange

    def open_dates(self, start: str, end: str) -> list[str]:
        return self._cal.get_open_trade_dates(
            start_date=start, end_date=end, exchange=self._exchange
        )

    def rebalance_dates(
        self,
        start: str,
        end: str,
        freq: str = "monthly",
    ) -> list[str]:
        """
        返回 [start, end] 内调仓日（升序）。
        monthly: 每月最后一个开市日
        weekly: 当周（周一~周日）最后一个开市日
        """
        opens = self.open_dates(start, end)
        if not opens:
            return []

        freq = (freq or "monthly").strip().lower()
        if freq == "weekly":
            return self._last_of_week(opens)
        return self._last_of_month(opens)

    @staticmethod
    def _last_of_month(opens: list[str]) -> list[str]:
        by_month: dict[str, str] = {}
        for d in opens:
            by_month[d[:6]] = d
        return [by_month[k] for k in sorted(by_month)]

    @staticmethod
    def _last_of_week(opens: list[str]) -> list[str]:
        by_week: dict[tuple[int, int], str] = {}
        for d in opens:
            dt = datetime.strptime(d, "%Y%m%d").date()
            iso = dt.isocalendar()
            by_week[(iso.year, iso.week)] = d
        return [by_week[k] for k in sorted(by_week)]
