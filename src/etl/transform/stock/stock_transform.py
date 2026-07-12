from __future__ import annotations

from typing import Dict, List

from src.common.function import report_period_generate
from src.entities.data_entities.stock.stock_list_entities import StockListEntities


def _norm_yyyymmdd(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 8:
        return digits[:8]
    return None


def _is_b_stock(ts_code: str) -> bool:
    """B 股：9009xx.SH（沪 B）或 200xxx.SZ（深 B）。"""
    if not ts_code or len(ts_code) < 6:
        return False
    code = ts_code[:6]
    return code.startswith("9009") or code.startswith("200")


class StockTransform:
    def period_stock_count(
        self,
        stock_rows: List[StockListEntities],
        start_date: str,
        end_date: str,
    ) -> Dict[str, int]:
        """
        根据 list_date、delist_date 统计各财报报告日（季末 YYYYMMDD）当日已在市股票数量。

        规则：list_date <= 报告期 且 (无 delist_date / 空 或 delist_date > 报告期)；B 股排除。
        """
        periods = report_period_generate(start_date, end_date)
        counts: Dict[str, int] = dict.fromkeys(periods, 0)
        if not periods or not stock_rows:
            return counts

        for row in stock_rows:
            ts_code = getattr(row, "ts_code", "") or ""
            if _is_b_stock(ts_code):
                continue
            ld = _norm_yyyymmdd(getattr(row, "list_date", None))
            if not ld:
                continue
            dd = _norm_yyyymmdd(getattr(row, "delist_date", None))
            for period in periods:
                if ld > period:
                    continue
                if dd is not None and dd <= period:
                    continue
                counts[period] = counts.get(period, 0) + 1

        return counts

    def build_active_count_rows(
        self,
        stock_rows: List[StockListEntities],
        date_keys: List[str],
        *,
        trade_date_set: set[str],
        suspend_by_code: dict[str, set[str]],
    ) -> List[dict[str, int | str | None]]:
        """
        聚合 stock_active_count 行。

        listed_count：date_key 当日未退市 A 股（排除 B 股）。
        trading_count：仅 SSE 开市日写入，= listed_count - 全天停牌数。
        """
        if not date_keys or not stock_rows:
            return []

        stocks: list[tuple[str, str, str | None]] = []
        for row in stock_rows:
            ts_code = getattr(row, "ts_code", "") or ""
            if _is_b_stock(ts_code):
                continue
            ld = _norm_yyyymmdd(getattr(row, "list_date", None))
            if not ld:
                continue
            dd = _norm_yyyymmdd(getattr(row, "delist_date", None))
            stocks.append((ts_code, ld, dd))

        rows: List[dict[str, int | str | None]] = []
        for dk in date_keys:
            listed = 0
            suspended = 0
            is_trade_day = dk in trade_date_set
            for ts_code, ld, dd in stocks:
                if ld > dk:
                    continue
                if dd is not None and dd <= dk:
                    continue
                listed += 1
                if is_trade_day and dk in suspend_by_code.get(ts_code, set()):
                    suspended += 1
            row: dict[str, int | str | None] = {
                "date_key": dk,
                "listed_count": listed,
            }
            if is_trade_day:
                row["trading_count"] = listed - suspended
            else:
                row["trading_count"] = None
            rows.append(row)
        return rows

    def trade_date_stock_count(
        self,
        stock_rows: List[StockListEntities],
        trade_dates: List[str],
    ) -> Dict[str, int]:
        """
        根据 list_date 统计各交易日当日已上市股票数量；已退市股票（delist_date 非空）整体排除。

        规则：list_date <= trade_date 且 delist_date 为空。
        """
        counts: Dict[str, int] = dict.fromkeys(trade_dates, 0)
        if not trade_dates or not stock_rows:
            return counts

        for row in stock_rows:
            ld = _norm_yyyymmdd(getattr(row, "list_date", None))
            if not ld:
                continue
            dd = _norm_yyyymmdd(getattr(row, "delist_date", None))
            if dd is not None:
                continue
            for td in trade_dates:
                if ld > td:
                    continue
                counts[td] = counts.get(td, 0) + 1

        return counts
