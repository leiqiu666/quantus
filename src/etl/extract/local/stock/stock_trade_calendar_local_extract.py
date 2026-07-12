"""交易日历本地 Extract：经 Service 读库。"""

from __future__ import annotations

from src.service.stock.stock_trade_cal_service import TradeCalService


class TradeCalLocalExtract:
    def __init__(self) -> None:
        self._service = TradeCalService()

    def get_max_cal_date(self, exchange: str) -> str | None:
        return self._service.get_max_cal_date(exchange)

    def get_min_cal_date(self, exchange: str) -> str | None:
        return self._service.get_min_cal_date(exchange)

    def get_open_trade_dates(
        self,
        *,
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
    ) -> list[str]:
        return self._service.get_open_trade_dates(
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
        )

    def resolve_incremental_start(
        self,
        *,
        exchange: str,
        configured_start: str,
    ) -> str:
        return self._service.resolve_incremental_start(
            exchange=exchange,
            configured_start=configured_start,
        )
