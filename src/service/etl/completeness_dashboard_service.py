"""Admin 量化数据源看板读聚合 Service。"""

from __future__ import annotations

import calendar
from datetime import datetime
from typing import Any

from src.common.function import (
    calendar_day_page_bounds,
    calendar_day_sequence,
    month_page_bounds,
    report_period_generate,
    report_period_page_bounds,
    trade_date_page_bounds,
)
from src.common.setting import settings
from src.model.etl.completeness_snapshot_model import CompletenessSnapshotModel
from src.model.stock.stock_suspend_model import StockSuspendModel
from src.service.etl.completeness_dashboard_config import (
    DashboardColumn,
    DashboardGroup,
    get_dashboard_group,
)
from src.service.financial.financial_report_service import ReportService
from src.service.kline.kline_daily_service import KlineDailyService
from src.service.stock.stock_active_count_service import StockActiveCountService
from src.service.stock.stock_trade_cal_service import TradeCalService


def _metric_from_counts(
    count: int,
    period_stock_count: int,
    threshold: float,
    *,
    has_snapshot: bool = True,
) -> dict[str, Any]:
    if not has_snapshot:
        return {
            "count": count,
            "period_stock_count": period_stock_count,
            "ratio": None,
            "is_complete": False,
            "has_snapshot": False,
            "threshold": threshold,
        }
    if threshold <= 0:
        is_complete = True
        ratio = 1.0 if period_stock_count > 0 else None
    elif period_stock_count > 0:
        ratio = count / period_stock_count
        is_complete = ratio >= threshold
    else:
        ratio = None
        is_complete = False
    return {
        "count": count,
        "period_stock_count": period_stock_count,
        "ratio": ratio,
        "is_complete": is_complete,
        "has_snapshot": True,
        "threshold": threshold,
    }


def _metric_from_snapshot(
    snap: dict | None,
    col: DashboardColumn,
    *,
    period_stock_count: int | None = None,
) -> dict[str, Any]:
    if snap is None:
        return _metric_from_counts(
            0, period_stock_count or 0, col.threshold, has_snapshot=False,
        )
    psc = (
        period_stock_count
        if period_stock_count is not None
        else snap["period_stock_count"]
    )
    return _metric_from_counts(
        snap["resolved_count"],
        psc,
        col.threshold,
        has_snapshot=True,
    )


def _row_complete(columns: dict[str, dict[str, Any]]) -> bool:
    metrics = [m for m in columns.values() if m.get("has_snapshot")]
    if not metrics:
        return False
    return all(m.get("is_complete") for m in metrics)


def _snapshot_lookup(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(r["source_name"], r["date_key"]): r for r in rows}


def _columns_meta(group: DashboardGroup) -> list[dict[str, Any]]:
    return [
        {
            "key": c.key,
            "label": c.label,
            "threshold": c.threshold,
            "sse_task_key": c.sse_task_key,
        }
        for c in group.columns
    ]


def _dashboard_env_default_start(group: DashboardGroup) -> str:
    if group.start_default_env:
        return settings.etl_start_date(group.start_default_env)
    return "19900101"


def _dashboard_range_bounds(
    group: DashboardGroup,
    *,
    start: str | None,
    end: str | None,
) -> tuple[str, str, str, str]:
    """返回 (default_start, default_end, start_bound, end_bound)。"""
    default_start_raw = _dashboard_env_default_start(group)
    today = datetime.now()
    if group.date_key_type == "month":
        default_start = (
            default_start_raw[:6] if len(default_start_raw) >= 6 else "199001"
        )
        default_end = today.strftime("%Y%m")
        start_bound = (start or default_start)[:6]
        end_bound = (end or default_end)[:6]
    else:
        default_start = default_start_raw
        default_end = today.strftime("%Y%m%d")
        start_bound = start or default_start
        end_bound = end or default_end
    return default_start, default_end, start_bound, end_bound


def _dashboard_meta(
    group: DashboardGroup,
    *,
    default_start: str,
    default_end: str,
) -> dict[str, Any]:
    return {
        "group_id": group.group_id,
        "title": group.title,
        "date_key_type": group.date_key_type,
        "date_label": group.date_label,
        "columns": _columns_meta(group),
        "default_start": default_start,
        "default_end": default_end,
    }


class CompletenessDashboardService:
    def __init__(self) -> None:
        self._snapshot_model = CompletenessSnapshotModel()
        self._report_service = ReportService()
        self._kline_service = KlineDailyService()
        self._suspend_model = StockSuspendModel()
        self._trade_cal = TradeCalService()
        self._active_count = StockActiveCountService()

    def get_dashboard(
        self,
        group_id: str,
        *,
        start: str | None = None,
        end: str | None = None,
        page: int = 1,
        count: int = 50,
    ) -> dict[str, Any]:
        group = get_dashboard_group(group_id)
        default_start, default_end, start_bound, end_bound = _dashboard_range_bounds(
            group, start=start, end=end,
        )
        meta = _dashboard_meta(
            group, default_start=default_start, default_end=default_end,
        )

        if start_bound > end_bound:
            return {
                "items": [],
                "total": 0,
                "meta": meta,
            }

        handler = {
            "financial_report_period": self._financial_report_period,
            "financial_ann_date": self._financial_ann_date,
            "kline_trade_date": self._kline_trade_date,
            "market_trade_date": self._market_trade_date,
            "index_trade_date": self._index_trade_date,
            "stock_basic_trade_date": self._stock_basic_trade_date,
            "index_month": self._index_month,
        }[group_id]

        items, total = handler(group, start_bound, end_bound, page, count)
        return {
            "items": items,
            "total": total,
            "meta": meta,
        }

    def _paginate_trade_dates(
        self,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[str], int, str | None, str | None]:
        open_dates = self._trade_cal.get_open_trade_dates(
            start_date=start, end_date=end, exchange="SSE",
        )
        total = len(open_dates)
        bounds = trade_date_page_bounds(start, end, page, count)
        if bounds is None:
            return [], total, None, None
        window_lo, window_hi = bounds
        page_dates = [d for d in reversed(open_dates) if window_lo <= d <= window_hi]
        return page_dates, total, window_lo, window_hi

    def _paginate_calendar_days(
        self,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[str], int, str | None, str | None]:
        total = len(calendar_day_sequence(start, end))
        bounds = calendar_day_page_bounds(start, end, page, count)
        if bounds is None:
            return [], total, None, None
        window_lo, window_hi = bounds
        page_days = [
            d for d in reversed(calendar_day_sequence(start, end))
            if window_lo <= d <= window_hi
        ]
        return page_days, total, window_lo, window_hi

    def _financial_report_period(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        all_periods = report_period_generate(start, end)
        total = len(all_periods)
        bounds = report_period_page_bounds(start, end, page, count)
        if bounds is None:
            return [], total
        window_lo, window_hi = bounds
        page_periods = [
            p for p in reversed(all_periods) if window_lo <= p <= window_hi
        ]
        rows_by_period = {
            row["report_period"]: row
            for row in self._report_service.get_period_list(
                start_period_date=window_lo,
                end_period_date=window_hi,
            )
        }
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        listed_counts = self._active_count.resolve_listed_counts(page_periods)
        items = []
        for period in page_periods:
            row = rows_by_period.get(period, {})
            psc = listed_counts.get(period, int(row.get("period_stock_count") or 0))
            columns: dict[str, dict] = {}
            for col in group.columns:
                if col.count_field:
                    cnt = int(row.get(col.count_field or "") or 0)
                    columns[col.key] = _metric_from_counts(cnt, psc, col.threshold)
                elif col.source_name:
                    columns[col.key] = _metric_from_snapshot(
                        snap_map.get((col.source_name, period)), col,
                        period_stock_count=psc,
                    )
            items.append({
                "date_key": period,
                "period_stock_count": psc,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _financial_ann_date(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        page_days, total, window_lo, window_hi = self._paginate_calendar_days(
            start, end, page, count,
        )
        if not page_days or window_lo is None or window_hi is None:
            return [], total
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        listed_counts = self._active_count.resolve_listed_counts_for_calendar_days(
            page_days,
        )
        items = []
        for dk in page_days:
            psc = listed_counts.get(dk, 0)
            columns: dict[str, dict] = {}
            for col in group.columns:
                columns[col.key] = _metric_from_snapshot(
                    snap_map.get((col.source_name or "", dk)), col,
                    period_stock_count=psc,
                )
            items.append({
                "date_key": dk,
                "period_stock_count": psc or None,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _kline_trade_date(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        page_dates, total, window_lo, window_hi = self._paginate_trade_dates(
            start, end, page, count,
        )
        if not page_dates or window_lo is None or window_hi is None:
            return [], total
        daily_by_date = {
            row["trade_date"]: int(row.get("kline_daily_count") or 0)
            for row in self._kline_service.list_trade_date_kline_counts(
                start_date=window_lo, end_date=window_hi,
            )
        }
        adj_by_date = {
            row["trade_date"]: int(row.get("kline_adj_factor_count") or 0)
            for row in self._kline_service.list_trade_date_adj_factor_counts(
                start_date=window_lo, end_date=window_hi,
            )
        }
        limit_by_date = {
            row["trade_date"]: int(row.get("kline_stk_limit_count") or 0)
            for row in self._kline_service.list_trade_date_stk_limit_counts(
                start_date=window_lo, end_date=window_hi,
            )
        }
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        trading_counts = self._active_count.resolve_trading_counts(page_dates)
        count_field_map = {
            "kline_daily_count": daily_by_date,
            "kline_adj_factor_count": adj_by_date,
            "kline_stk_limit_count": limit_by_date,
        }
        items = []
        for td in page_dates:
            psc = trading_counts.get(td, 0)
            columns: dict[str, dict] = {}
            for col in group.columns:
                if col.count_field:
                    cnt = count_field_map.get(col.count_field, {}).get(td, 0)
                    columns[col.key] = _metric_from_counts(cnt, psc, col.threshold)
                elif col.source_name:
                    columns[col.key] = _metric_from_snapshot(
                        snap_map.get((col.source_name, td)), col,
                        period_stock_count=psc,
                    )
            items.append({
                "date_key": td,
                "period_stock_count": psc,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _market_trade_date(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        page_dates, total, window_lo, window_hi = self._paginate_trade_dates(
            start, end, page, count,
        )
        if not page_dates or window_lo is None or window_hi is None:
            return [], total
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        trading_counts = self._active_count.resolve_trading_counts(page_dates)
        items = []
        for td in page_dates:
            psc = trading_counts.get(td, 0)
            columns: dict[str, dict] = {}
            for col in group.columns:
                columns[col.key] = _metric_from_snapshot(
                    snap_map.get((col.source_name or "", td)), col,
                    period_stock_count=psc,
                )
            items.append({
                "date_key": td,
                "period_stock_count": psc or None,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _stock_basic_trade_date(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        page_dates, total, window_lo, window_hi = self._paginate_trade_dates(
            start, end, page, count,
        )
        if not page_dates or window_lo is None or window_hi is None:
            return [], total
        suspend_counts = self._suspend_model.count_by_trade_dates(page_dates)
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        trading_counts = self._active_count.resolve_trading_counts(page_dates)
        items = []
        for td in page_dates:
            psc = trading_counts.get(td, 0)
            columns: dict[str, dict] = {}
            for col in group.columns:
                if col.count_field:
                    cnt = suspend_counts.get(td, 0)
                    columns[col.key] = _metric_from_counts(
                        cnt, 0, col.threshold, has_snapshot=True,
                    )
                elif col.source_name:
                    columns[col.key] = _metric_from_snapshot(
                        snap_map.get((col.source_name, td)), col,
                        period_stock_count=psc,
                    )
            items.append({
                "date_key": td,
                "period_stock_count": psc or None,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _index_trade_date(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        page_dates, total, window_lo, window_hi = self._paginate_trade_dates(
            start, end, page, count,
        )
        if not page_dates or window_lo is None or window_hi is None:
            return [], total
        snap_sources = [c.source_name for c in group.columns if c.source_name]
        snaps = self._snapshot_model.list_by_sources_and_range(
            snap_sources, start=window_lo, end=window_hi,
        )
        snap_map = _snapshot_lookup(snaps)
        items = []
        for td in page_dates:
            columns: dict[str, dict] = {}
            for col in group.columns:
                if col.source_name:
                    snap = snap_map.get((col.source_name, td))
                    psc = int(snap["period_stock_count"]) if snap else 0
                    columns[col.key] = _metric_from_snapshot(
                        snap, col, period_stock_count=psc,
                    )
            items.append({
                "date_key": td,
                "period_stock_count": None,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total

    def _index_month(
        self,
        group: DashboardGroup,
        start: str,
        end: str,
        page: int,
        count: int,
    ) -> tuple[list[dict], int]:
        from src.common.function import _month_sequence

        all_months = _month_sequence(start, end)
        total = len(all_months)
        bounds = month_page_bounds(start, end, page, count)
        if bounds is None:
            return [], total
        window_lo, window_hi = bounds
        page_months = [m for m in reversed(all_months) if window_lo <= m <= window_hi]
        page_months.sort(reverse=True)
        source_names = [c.source_name for c in group.columns if c.source_name]
        items = []
        for ym in page_months:
            y, m = int(ym[:4]), int(ym[4:6])
            last_day = calendar.monthrange(y, m)[1]
            month_start = f"{ym}01"
            month_end = f"{ym}{last_day:02d}"
            snaps = self._snapshot_model.list_by_sources_and_range(
                source_names, start=month_start, end=month_end,
            )
            columns: dict[str, dict] = {}
            for col in group.columns:
                if col.source_name:
                    month_snaps = [s for s in snaps if s["source_name"] == col.source_name]
                    if not month_snaps:
                        columns[col.key] = _metric_from_snapshot(None, col)
                        continue
                    best = max(month_snaps, key=lambda s: s["resolved_count"])
                    columns[col.key] = _metric_from_snapshot(best, col)
                elif col.sse_task_key:
                    columns[col.key] = _metric_from_counts(
                        0, 0, col.threshold, has_snapshot=False,
                    )
            items.append({
                "date_key": ym,
                "period_stock_count": None,
                "columns": columns,
                "row_complete": _row_complete(columns),
            })
        return items, total
