"""K 线日线本地 Extract：经 Service 读库。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.service.kline.kline_daily_service import KlineDailyService

_COMPLETE_THRESHOLD = 0.95


class KlineLocalExtract:
    def __init__(self) -> None:
        self._service = KlineDailyService()

    def get_max_trade_date(self) -> str | None:
        return self._service.get_max_trade_date()

    def resolve_incremental_start(self, configured_start: str) -> str:
        return self._service.resolve_incremental_start(configured_start)

    def get_trade_date_list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """各交易日 kline_daily 条数。每项含 trade_date、kline_daily_count。"""
        return self._service.list_trade_date_kline_counts(
            start_date=start_date,
            end_date=end_date,
        )

    def get_kline_daily_period_count(self) -> List[Dict[str, Any]]:
        """从库表 kline_daily_period_count 拉取全量快照（无筛选）。"""
        return self._service.list_kline_daily_period_count()

    # 三维度共享同一份快照表，仅 count 列不同；保留 3 个名字便于 Strategy 按维度寻址。
    get_kline_adj_factor_period_count = get_kline_daily_period_count
    get_kline_stk_limit_period_count = get_kline_daily_period_count

    def _trade_date_filter_below_threshold(
        self,
        count_field: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        threshold: float = _COMPLETE_THRESHOLD,
    ) -> List[str]:
        """根据 kline_daily_period_count 快照筛选 ``count_field < threshold × stock_n`` 的交易日。"""
        rows = self.get_kline_daily_period_count()
        missing: List[str] = []
        for row in rows:
            td = row.get("trade_date")
            if not td:
                continue
            stock_n = row.get("period_stock_count")
            if stock_n is None or stock_n <= 0:
                continue
            if start_date is not None and td < start_date:
                continue
            if end_date is not None and td > end_date:
                continue
            cnt = row.get(count_field) or 0
            if cnt < threshold * stock_n:
                missing.append(td)
        return sorted(set(missing), reverse=True)

    def trade_date_filter_by_kline_count(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """筛选日线数据不足的交易日（95% 规则）。"""
        return self._trade_date_filter_below_threshold(
            "kline_daily_count", start_date=start_date, end_date=end_date,
        )

    def trade_date_filter_by_adj_factor_count(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """筛选复权因子数据不足的交易日（95% 规则）。"""
        return self._trade_date_filter_below_threshold(
            "kline_adj_factor_count", start_date=start_date, end_date=end_date,
        )

    def trade_date_filter_by_stk_limit_count(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """筛选涨跌停数据不足的交易日（95% 规则）。"""
        return self._trade_date_filter_below_threshold(
            "kline_stk_limit_count", start_date=start_date, end_date=end_date,
        )

    def get_kline_daily_by_trade_date(self, trade_date: str) -> List[Dict[str, Any]]:
        """按交易日读取库内已有日线（经 Service → Model）。"""
        return self._service.list_kline_daily_by_trade_date(trade_date)

    def effective_complete_end_trade_date(
        self,
        open_trade_dates: List[str],
        calendar_end: str,
        period_count_rows: List[Dict[str, Any]],
        count_field: str,
        *,
        threshold: float = _COMPLETE_THRESHOLD,
    ) -> str:
        """
        微观完整性检查的有效截止日。

        若 calendar_end 对应开市日宏观条数未达 threshold（如当日 Tushare 尚未发布），
        回退至不晚于 calendar_end 的最近达标开市日，避免误判逐股缺数并触发无效补拉。
        """
        if not open_trade_dates or not calendar_end:
            return calendar_end

        candidates = [td for td in open_trade_dates if td <= calendar_end]
        if not candidates:
            return calendar_end

        by_date: Dict[str, Dict[str, Any]] = {}
        for row in period_count_rows:
            td = str(row.get("trade_date", "")).strip()
            if td:
                by_date[td] = row

        for td in reversed(candidates):
            row = by_date.get(td)
            if row is None:
                continue
            stock_n = row.get("period_stock_count") or 0
            cnt = row.get(count_field) or 0
            if stock_n > 0 and cnt >= threshold * stock_n:
                return td

        if len(candidates) >= 2 and candidates[-1] == calendar_end:
            return candidates[-2]
        return candidates[-1]
