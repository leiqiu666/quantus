from __future__ import annotations

from typing import Iterable, List

import pandas as pd

from src.etl.extract.local.stock.stock_local_extract import StockExtract


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


class KlineTransform:
    def expected_trade_dates_for_stock(
        self,
        open_trade_dates: List[str],
        list_date: str | None,
        delist_date: str | None,
        start_date: str,
        end_date: str,
        *,
        full_day_suspend_dates: Iterable[str] | None = None,
    ) -> List[str]:
        """
        在 [start_date, end_date] 内，取 SSE 开市日与该股上市存续期的交集，
        再扣除全天停牌日。

        规则：
        - list_date <= trade_date 且 (无 delist_date 或 delist_date > trade_date)
          （与 StockTransform.trade_date_stock_count 在市口径一致：list_date <= trade_date 且未退市）
        - trade_date not in full_day_suspend_dates（来自 suspend_d，type=S 且 timing=''）

        full_day_suspend_dates 为 None 或空时行为不变（向后兼容）。
        """
        if not start_date or not end_date or start_date > end_date:
            return []

        ld = _norm_yyyymmdd(list_date)
        dd = _norm_yyyymmdd(delist_date)
        suspend_set: set[str] = set(full_day_suspend_dates) if full_day_suspend_dates else set()
        result: List[str] = []
        for td in open_trade_dates:
            if td < start_date or td > end_date:
                continue
            if ld and ld > td:
                continue
            if dd is not None and dd <= td:
                continue
            if td in suspend_set:
                continue
            result.append(td)
        return result

    def check_kline_daily_complete_by_trade_dates(
        self,
        resolved_trade_dates: List[str],
        expected_trade_dates: List[str],
    ) -> List[str]:
        """expected 与 resolved 做差集，返回缺失 trade_date（保持 expected 顺序）。"""
        if not expected_trade_dates:
            return []
        resolved_set = set(resolved_trade_dates)
        return [td for td in expected_trade_dates if td not in resolved_set]

    def merge_consecutive_trade_dates(
        self,
        dates: List[str],
        *,
        open_trade_dates: List[str],
    ) -> List[tuple[str, str]]:
        """
        将升序缺日按开市日序列中的相邻关系合并为区间 [start, end]。

        open_trade_dates 须为升序 SSE 开市日列表，用于判定两个缺日是否相邻。
        """
        if not dates:
            return []

        idx = {d: i for i, d in enumerate(open_trade_dates)}
        sorted_missing = sorted(dates, key=lambda d: idx.get(d, d))
        ranges: List[tuple[str, str]] = []
        start = end = sorted_missing[0]
        for td in sorted_missing[1:]:
            prev_i = idx.get(end)
            cur_i = idx.get(td)
            if prev_i is not None and cur_i is not None and cur_i == prev_i + 1:
                end = td
            else:
                ranges.append((start, end))
                start = end = td
        ranges.append((start, end))
        return ranges

    def filter_by_listed_stock(
        self,
        trade_date: str,
        df: pd.DataFrame,
        *,
        stock_extract: StockExtract | None = None,
    ) -> pd.DataFrame:
        """
        按交易日在市名单过滤 K 线 / 复权因子：剔除该日未在市（未上市或已退市）的股票。

        trade_date 为 8 位 YYYYMMDD；df 须含 ts_code。
        规则与 ReportTransform.filter_report_by_delist、StockListModel 报告期在市筛选一致。
        """
        if df is None or df.empty:
            return df.copy() if df is not None else pd.DataFrame()

        td = (trade_date or "").strip()
        if not td:
            return df.iloc[0:0].copy()

        out = df.copy()
        if "trade_date" in out.columns:
            out = out.loc[
                out["trade_date"].astype(str).str.strip().str[:8] == td
            ]

        extractor = stock_extract if stock_extract is not None else StockExtract()
        listed = extractor.get_stock_list(period=td)
        allowed = {str(r.ts_code).strip() for r in listed if r.ts_code}
        if not allowed:
            return out.iloc[0:0].copy()

        return out.loc[
            out["ts_code"].astype(str).str.strip().isin(allowed)
        ].copy()
