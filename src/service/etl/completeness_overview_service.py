"""量化数据源总览看板：跨分组聚合 + 缺口清单 + 关键路径滞后 + 调度摘要。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.model.kline.kline_daily_model import KlineDailyModel
from src.model.scheduler.schedule_job_model import ScheduleJobModel
from src.service.etl.completeness_dashboard_config import (
    DASHBOARD_GROUPS,
    DashboardGroup,
    GROUP_DETAIL_PATHS,
)
from src.service.etl.completeness_dashboard_service import CompletenessDashboardService
from src.service.scheduler.schedule_run_service import ScheduleRunService
from src.service.stock.stock_active_count_service import StockActiveCountService
from src.service.stock.stock_trade_cal_service import TradeCalService


def _days_between(early: str, late: str) -> int:
    d1 = datetime.strptime(early[:8], "%Y%m%d").date()
    d2 = datetime.strptime(late[:8], "%Y%m%d").date()
    return max(0, (d2 - d1).days)


def _group_status(complete_rate: float, *, all_complete: bool) -> str:
    if all_complete:
        return "healthy"
    if complete_rate >= 0.8:
        return "warning"
    return "critical"


class CompletenessOverviewService:
    def __init__(self) -> None:
        self._dashboard = CompletenessDashboardService()
        self._trade_cal = TradeCalService()
        self._active_count = StockActiveCountService()
        self._kline_model = KlineDailyModel()
        self._schedule_runs = ScheduleRunService()
        self._schedule_jobs = ScheduleJobModel()

    def get_overview(self, *, window: int = 5) -> dict[str, Any]:
        window = max(1, min(window, 30))
        today = datetime.now().strftime("%Y%m%d")
        latest_trade = self._trade_cal.get_nearest_open_trade_date_on_or_before(today)
        open_today = self._trade_cal.get_open_trade_dates(
            start_date=today, end_date=today,
        )
        is_trading_day = today in open_today

        groups_out: list[dict[str, Any]] = []
        all_gaps: list[dict[str, Any]] = []
        source_total = 0
        groups_healthy = 0
        gap_cell_count = 0

        for group_id, group in DASHBOARD_GROUPS.items():
            source_total += len(group.columns)
            dash = self._dashboard.get_dashboard(
                group_id,
                end=None,
                page=1,
                count=window,
            )
            items = dash["items"]
            columns_meta = dash["meta"]["columns"]
            summary, gaps = self._summarize_group(group, items, columns_meta)
            summary["detail_path"] = GROUP_DETAIL_PATHS.get(group_id, "")
            groups_out.append(summary)
            all_gaps.extend(gaps)
            gap_cell_count += summary["gap_cell_count"]
            if summary["status"] == "healthy":
                groups_healthy += 1

        all_gaps.sort(key=lambda g: g["date_key"], reverse=True)
        gap_items = all_gaps[:20]

        active_row = None
        if latest_trade:
            ac = self._active_count.resolve_listed_count(latest_trade)
            tc = self._active_count.resolve_trading_count(latest_trade)
            active_row = {
                "date_key": latest_trade,
                "listed_count": ac,
                "trading_count": tc,
            }

        return {
            "as_of": today,
            "latest_trade_date": latest_trade,
            "is_trading_day": is_trading_day,
            "window": window,
            "source_total": source_total,
            "group_total": len(DASHBOARD_GROUPS),
            "groups_healthy": groups_healthy,
            "gap_cell_count": gap_cell_count,
            "active_stock": active_row,
            "groups": groups_out,
            "gaps": gap_items,
            "key_paths": self._key_path_lags(latest_trade),
            "scheduler": self._scheduler_summary(),
        }

    def _summarize_group(
        self,
        group: DashboardGroup,
        items: list[dict],
        columns_meta: list[dict],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        col_meta = {c["key"]: c for c in columns_meta}
        total_cells = 0
        complete_cells = 0
        gaps: list[dict[str, Any]] = []
        worst_ratio: float | None = None
        worst_col: dict[str, Any] | None = None
        latest_gap_dk: str | None = None

        for row in items:
            dk = row["date_key"]
            for col in group.columns:
                metric = row["columns"].get(col.key, {})
                if col.threshold <= 0:
                    continue
                total_cells += 1
                if metric.get("is_complete"):
                    complete_cells += 1
                else:
                    if latest_gap_dk is None or dk > latest_gap_dk:
                        latest_gap_dk = dk
                    meta = col_meta.get(col.key, {})
                    gaps.append({
                        "group_id": group.group_id,
                        "group_title": group.title,
                        "date_key": dk,
                        "date_key_type": group.date_key_type,
                        "column_key": col.key,
                        "column_label": col.label,
                        "ratio": metric.get("ratio"),
                        "threshold": col.threshold,
                        "sse_task_key": meta.get("sse_task_key") or col.sse_task_key,
                    })
                ratio = metric.get("ratio")
                if ratio is not None and (
                    worst_ratio is None or ratio < worst_ratio
                ):
                    worst_ratio = ratio
                    worst_col = {
                        "key": col.key,
                        "label": col.label,
                        "ratio": ratio,
                    }

        complete_rate = complete_cells / total_cells if total_cells else 1.0
        all_complete = total_cells > 0 and complete_cells == total_cells
        rows_complete = sum(1 for r in items if r.get("row_complete"))
        return {
            "group_id": group.group_id,
            "title": group.title,
            "date_label": group.date_label,
            "date_key_type": group.date_key_type,
            "column_count": len(group.columns),
            "window_row_count": len(items),
            "rows_complete": rows_complete,
            "complete_rate": round(complete_rate, 4),
            "gap_cell_count": total_cells - complete_cells,
            "status": _group_status(complete_rate, all_complete=all_complete),
            "worst_column": worst_col,
            "latest_gap_date_key": latest_gap_dk,
        }, gaps

    def _key_path_lags(self, latest_trade: str | None) -> list[dict[str, Any]]:
        if not latest_trade:
            return []
        ref = latest_trade
        paths: list[tuple[str, str | None]] = [
            ("日K", self._kline_model.get_max_trade_date()),
        ]
        result: list[dict[str, Any]] = []
        for name, latest_date in paths:
            if not latest_date:
                result.append({
                    "name": name,
                    "latest_date": None,
                    "reference_date": ref,
                    "lag_days": None,
                    "status": "unknown",
                })
                continue
            lag = _days_between(latest_date, ref)
            status = "ok" if lag <= 1 else ("warning" if lag <= 3 else "critical")
            result.append({
                "name": name,
                "latest_date": latest_date,
                "reference_date": ref,
                "lag_days": lag,
                "status": status,
            })
        return result

    def _scheduler_summary(self) -> dict[str, Any]:
        recent = self._schedule_runs.recent_runs(limit=5)
        today = datetime.now().strftime("%Y%m%d")
        today_runs = [
            r for r in recent
            if r.get("started_at") and r["started_at"][:10].replace("-", "") == today
        ]
        return {
            "jobs_enabled_count": self._schedule_jobs.count_enabled_jobs(),
            "last_run_at": self._schedule_runs.last_run_at(),
            "today_run_count": len(today_runs),
            "today_success_count": sum(
                1 for r in today_runs if r.get("status") == "success"
            ),
            "recent_runs": recent,
        }
