"""每日活跃股票数读服务：统一 listed / trading 分母口径。"""

from __future__ import annotations

from src.model.stock.stock_active_count_model import StockActiveCountModel
from src.service.stock.stock_trade_cal_service import TradeCalService


class StockActiveCountService:
    def __init__(self) -> None:
        self._model = StockActiveCountModel()
        self._trade_cal = TradeCalService()

    def resolve_listed_count(self, date_key: str) -> int:
        row = self._model.get_by_date_key(date_key)
        if row is None:
            return 0
        return int(row["listed_count"] or 0)

    def resolve_trading_count(self, date_key: str) -> int:
        ref_date = self._trade_cal.get_nearest_open_trade_date_on_or_before(date_key)
        if not ref_date:
            return 0
        row = self._model.get_by_date_key(ref_date)
        if row is None or row["trading_count"] is None:
            return 0
        return int(row["trading_count"] or 0)

    def resolve_listed_counts(self, date_keys: list[str]) -> dict[str, int]:
        stored = self._model.list_by_date_keys(date_keys)
        return {dk: int(stored[dk]["listed_count"]) for dk in date_keys if dk in stored}

    def resolve_trading_counts(self, date_keys: list[str]) -> dict[str, int]:
        ref_by_key: dict[str, str] = {}
        ref_dates: set[str] = set()
        for dk in date_keys:
            ref = self._trade_cal.get_nearest_open_trade_date_on_or_before(dk)
            if ref:
                ref_by_key[dk] = ref
                ref_dates.add(ref)
        stored = self._model.list_by_date_keys(sorted(ref_dates))
        result: dict[str, int] = {}
        for dk in date_keys:
            ref = ref_by_key.get(dk)
            if not ref or ref not in stored:
                result[dk] = 0
                continue
            tc = stored[ref].get("trading_count")
            result[dk] = int(tc or 0) if tc is not None else 0
        return result

    def resolve_listed_counts_for_calendar_days(
        self, date_keys: list[str],
    ) -> dict[str, int]:
        """自然日 → 映射到 <= 该日的最近开市日，取 listed_count 作公告日完整性分母。"""
        ref_by_key: dict[str, str] = {}
        ref_dates: set[str] = set()
        for dk in date_keys:
            ref = self._trade_cal.get_nearest_open_trade_date_on_or_before(dk)
            if ref:
                ref_by_key[dk] = ref
                ref_dates.add(ref)
        stored = self._model.list_by_date_keys(sorted(ref_dates))
        result: dict[str, int] = {}
        for dk in date_keys:
            ref = ref_by_key.get(dk)
            if not ref or ref not in stored:
                result[dk] = 0
                continue
            result[dk] = int(stored[ref]["listed_count"] or 0)
        return result
