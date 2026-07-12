"""交易日历查询服务（仅读库，不依赖 ETL）。"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.model.stock.stock_trade_calendar_model import TradeCalModel


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


class TradeCalService:
    def __init__(self) -> None:
        self._model = TradeCalModel()

    def get_max_cal_date(self, exchange: str) -> str | None:
        """指定交易所已入库的最大 cal_date。"""
        return self._model.get_max_cal_date(exchange)

    def get_min_cal_date(self, exchange: str) -> str | None:
        """指定交易所已入库的最小 cal_date。"""
        return self._model.get_min_cal_date(exchange)

    def get_open_trade_dates(
        self,
        *,
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
    ) -> list[str]:
        """返回区间内开市日（is_open=1），升序。"""
        return self._model.get_open_trade_dates(
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )

    def get_nearest_open_trade_date_on_or_before(
        self,
        date_key: str,
        *,
        exchange: str = "SSE",
    ) -> str | None:
        """返回 <= date_key 的最近开市日。"""
        return self._model.get_nearest_open_trade_date_on_or_before(
            date_key, exchange=exchange,
        )

    def resolve_incremental_start(
        self,
        *,
        exchange: str,
        configured_start: str,
    ) -> str:
        """
        增量同步起点：max(配置起始日, 库内最大 cal_date 的下一自然日)。

        库内无数据时返回 configured_start。
        """
        floor = (configured_start or "").strip()
        if not floor:
            return ""

        last = self.get_max_cal_date(exchange)
        if not last:
            return floor
        nxt = _ymd_add_days(last, 1)
        return max(floor, nxt)
