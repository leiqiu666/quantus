"""K 线 Workflow 层：单股 / 单日编排，三维度（daily / adj_factor / stk_limit）共享同一份实现。"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd

from src.etl.extract.kline.kline_extract import KlineExtract
from src.etl.extract.local.kline.kline_local_extract import KlineLocalExtract
from src.etl.extract.local.stock.stock_local_extract import StockExtract as LocalStockExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.etl.load.kline.kline_load import KlineLoad
from src.etl.log.missing_log import MissingLog
from src.etl.transform.kline.kline_transform import KlineTransform
from src.service.kline.kline_daily_service import KlineDailyService
from src.service.stock.stock_active_count_service import StockActiveCountService

# 单次 daily 约 6000 条；按 260 交易日/年 ≈ 23 年。A 股自 1990 起两段请求足够覆盖。
_SPLIT_CALENDAR_YEARS = 23
KLINE_DAILY_MISSING_ENTITY = "kline_daily"
KLINE_ADJ_FACTOR_MISSING_ENTITY = "kline_adj_factor"
KLINE_STK_LIMIT_MISSING_ENTITY = "kline_stk_limit"


@dataclass(frozen=True)
class _KlineWorkflowSpec:
    """三维度共享 workflow 行为的参数化点。"""

    name: str                          # daily / adj_factor / stk_limit
    missing_entity: str
    extract_range_method: str          # KlineExtract.pull_kline_*_range
    extract_by_date_method: str        # KlineExtract.pull_kline_*_by_date
    load_method: str                   # KlineLoad.load_kline_* (无 filter)
    resolved_dates_service_method: str # KlineDailyService.get_trade_dates_*_by_ts_code
    split_calendar_years: Optional[int] = None  # 仅 daily 设 23（其余 None）
    by_date_use_filter: bool = False             # 仅 daily 走 load_kline_daily_filter
    dimension_for_bulk_load: str = ""            # daily / adj_factor / stk_limit, 供 list_resolved_trade_dates_grouped 用


_KLINE_WORKFLOW_SPECS: dict[str, _KlineWorkflowSpec] = {
    "daily": _KlineWorkflowSpec(
        name="daily",
        missing_entity=KLINE_DAILY_MISSING_ENTITY,
        extract_range_method="pull_kline_daily_range",
        extract_by_date_method="pull_kline_daily_by_date",
        load_method="load_kline_daily",
        resolved_dates_service_method="get_trade_dates_by_ts_code",
        split_calendar_years=_SPLIT_CALENDAR_YEARS,
        by_date_use_filter=True,
        dimension_for_bulk_load="daily",
    ),
    "adj_factor": _KlineWorkflowSpec(
        name="adj_factor",
        missing_entity=KLINE_ADJ_FACTOR_MISSING_ENTITY,
        extract_range_method="pull_kline_adj_factor_range",
        extract_by_date_method="pull_kline_adj_factor_by_date",
        load_method="load_kline_adj_factor",
        resolved_dates_service_method="get_trade_dates_with_adj_factor_by_ts_code",
        dimension_for_bulk_load="adj_factor",
    ),
    "stk_limit": _KlineWorkflowSpec(
        name="stk_limit",
        missing_entity=KLINE_STK_LIMIT_MISSING_ENTITY,
        extract_range_method="pull_kline_stk_limit_range",
        extract_by_date_method="pull_kline_stk_limit_by_date",
        load_method="load_kline_stk_limit",
        resolved_dates_service_method="get_trade_dates_with_stk_limit_by_ts_code",
        dimension_for_bulk_load="stk_limit",
    ),
}


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


def _ymd_sub_calendar_years(ymd: str, years: int) -> str:
    """end_date 倒推 years 个日历年，尽量保持月日（处理闰年 2 月）。"""
    dt = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    y = dt.year - years
    m = dt.month
    d = min(dt.day, calendar.monthrange(y, m)[1])
    return date(y, m, d).strftime("%Y%m%d")


def _merge_daily_parts(parts: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [p for p in parts if p is not None and not p.empty]
    if not usable:
        return pd.DataFrame()
    out = pd.concat(usable, ignore_index=True)
    if "trade_date" in out.columns and "ts_code" in out.columns:
        out = out.drop_duplicates(subset=["ts_code", "trade_date"], keep="first")
    return out


class KlineWorkflow:
    def __init__(self):
        self.kline_extract = KlineExtract()
        self.kline_load = KlineLoad()
        self.local_kline_extract = KlineLocalExtract()
        self.local_stock_extract = LocalStockExtract()
        self.trade_cal_local = TradeCalLocalExtract()
        self.active_count_service = StockActiveCountService()
        self.kline_transform = KlineTransform()
        self.kline_daily_service = KlineDailyService()
        self.missing_log = MissingLog()

    # ---------- 内部统一实现 ----------

    def _resolve_spec(self, dimension: str) -> _KlineWorkflowSpec:
        spec = _KLINE_WORKFLOW_SPECS.get(dimension)
        if spec is None:
            raise ValueError(f"未知 K 线维度: {dimension}")
        return spec

    def preload_resolved_trade_dates(
        self,
        dimension: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, list[str]]:
        """完整性校验前一次性加载全市场 (ts_code → resolved trade_dates)，消除逐股查询。"""
        spec = self._resolve_spec(dimension)
        return self.kline_daily_service.list_resolved_trade_dates_grouped(
            dimension=spec.dimension_for_bulk_load,
            start_date=start_date,
            end_date=end_date,
        )

    def _pull_range(
        self,
        spec: _KlineWorkflowSpec,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> int:
        """单股区间拉取并 upsert（仅 daily 触发 23 年拆段）。"""
        code = ts_code.strip()
        start = start_date.strip()
        end = end_date.strip()
        if not code or not start or not end or start > end:
            return 0

        extract_method = getattr(self.kline_extract, spec.extract_range_method)

        if spec.split_calendar_years is not None:
            boundary = _ymd_sub_calendar_years(end, spec.split_calendar_years)
            if start < boundary:
                df1 = extract_method(ts_code=code, start_date=start, end_date=boundary)
                nxt = _ymd_add_days(boundary, 1)
                df2 = (
                    extract_method(ts_code=code, start_date=nxt, end_date=end)
                    if nxt <= end
                    else pd.DataFrame()
                )
                df = _merge_daily_parts([df1, df2])
            else:
                df = extract_method(ts_code=code, start_date=start, end_date=end)
        else:
            df = extract_method(ts_code=code, start_date=start, end_date=end)

        load_method = getattr(self.kline_load, spec.load_method)
        return load_method(df)

    def _check_complete_by_ts_code(
        self,
        spec: _KlineWorkflowSpec,
        *,
        ts_code: str,
        list_date: str | None,
        delist_date: str | None,
        start_date: str,
        end_date: str,
        open_trade_dates: list[str] | None = None,
        resolved_trade_dates: list[str] | None = None,
        full_day_suspend_dates: set[str] | list[str] | None = None,
    ) -> list[str]:
        """单股完整性检查 + 按连续区间补拉。

        full_day_suspend_dates：该股在 [start, end] 内的全天停牌日（suspend_d
        中 suspend_type='S' 且 suspend_timing=''）。这些日子从 expected 中扣除，
        避免把停牌日误判为缺日。批量场景通常由 Strategy 层一次性预加载后传入。
        """
        code = (ts_code or "").strip()
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not code or not start or not end or start > end:
            return []

        if open_trade_dates is None:
            open_trade_dates = self.trade_cal_local.get_open_trade_dates(
                start_date=start, end_date=end, exchange="SSE"
            )

        expected_trade_dates = self.kline_transform.expected_trade_dates_for_stock(
            open_trade_dates, list_date, delist_date, start, end,
            full_day_suspend_dates=full_day_suspend_dates,
        )
        if not expected_trade_dates:
            return []

        if resolved_trade_dates is None:
            resolve_fn = getattr(
                self.kline_daily_service, spec.resolved_dates_service_method
            )
            resolved_trade_dates = resolve_fn(
                code, start_date=start, end_date=end
            )

        missing_dates = self.kline_transform.check_kline_daily_complete_by_trade_dates(
            resolved_trade_dates, expected_trade_dates,
        )
        if not missing_dates:
            return []

        self.missing_log.upsert_missing_logs(
            missing_items=[f"{code},{td}" for td in missing_dates],
            missing_entity=spec.missing_entity,
        )

        open_in_range = [td for td in open_trade_dates if start <= td <= end]
        ranges = self.kline_transform.merge_consecutive_trade_dates(
            missing_dates, open_trade_dates=open_in_range,
        )

        succeeded: list[str] = []
        failed: list[str] = []
        for range_start, range_end in ranges:
            range_missing = [
                td for td in missing_dates if range_start <= td <= range_end
            ]
            saved_count = self._pull_range(
                spec, ts_code=code, start_date=range_start, end_date=range_end,
            )
            if saved_count == 0:
                failed.extend(range_missing)
            else:
                succeeded.extend(range_missing)

        # 终态分两批合并写：每股至多 1 次 delete（成功）+ 1 次 upsert（失败），无论区间数
        if succeeded:
            self.missing_log.delete_missing_logs(
                missing_items=[f"{code},{td}" for td in succeeded],
                missing_entity=spec.missing_entity,
            )
        if failed:
            self.missing_log.upsert_missing_logs(
                missing_items=[f"{code},{td}" for td in failed],
                missing_entity=spec.missing_entity,
            )

        return missing_dates

    def _pull_by_date(self, spec: _KlineWorkflowSpec, *, trade_date: str) -> int:
        """按交易日拉取全市场并 upsert（daily 走 filter，其余走 plain upsert）。"""
        extract_method = getattr(self.kline_extract, spec.extract_by_date_method)
        df = extract_method(trade_date=trade_date)
        df = self.kline_transform.filter_by_listed_stock(
            trade_date, df, stock_extract=self.local_stock_extract,
        )
        if spec.by_date_use_filter:
            load_result = self.kline_load.load_kline_daily_filter(
                df,
                scope_trade_date=trade_date,
                local_kline_extract=self.local_kline_extract,
            )
            return load_result.total_written
        load_method = getattr(self.kline_load, spec.load_method)
        return load_method(df)

    # ---------- 公开 API（薄壳） ----------

    def pull_kline_daily_by_date(self, *, trade_date: str) -> int:
        """按交易日拉全市场日线，先查再改再插写入 kline_daily。"""
        return self._pull_by_date(self._resolve_spec("daily"), trade_date=trade_date)

    def pull_kline_adj_factor_by_date(self, *, trade_date: str) -> int:
        """按交易日拉全市场复权因子并 upsert 至 kline_daily.adj_factor。"""
        return self._pull_by_date(
            self._resolve_spec("adj_factor"), trade_date=trade_date
        )

    def pull_kline_stk_limit_by_date(self, *, trade_date: str) -> int:
        """按交易日拉全市场涨跌停价并 upsert 至 kline_daily.up_limit/down_limit。"""
        return self._pull_by_date(
            self._resolve_spec("stk_limit"), trade_date=trade_date
        )

    def check_kline_daily_complete_by_ts_code(
        self,
        *,
        ts_code: str,
        list_date: str | None,
        delist_date: str | None,
        start_date: str,
        end_date: str,
        open_trade_dates: list[str] | None = None,
        resolved_trade_dates: list[str] | None = None,
        full_day_suspend_dates: set[str] | list[str] | None = None,
    ) -> list[str]:
        """检查单股区间日线完整性，缺日写 log 并按连续区间补拉。"""
        return self._check_complete_by_ts_code(
            self._resolve_spec("daily"),
            ts_code=ts_code, list_date=list_date, delist_date=delist_date,
            start_date=start_date, end_date=end_date,
            open_trade_dates=open_trade_dates,
            resolved_trade_dates=resolved_trade_dates,
            full_day_suspend_dates=full_day_suspend_dates,
        )

    def check_kline_adj_factor_complete_by_ts_code(
        self,
        *,
        ts_code: str,
        list_date: str | None,
        delist_date: str | None,
        start_date: str,
        end_date: str,
        open_trade_dates: list[str] | None = None,
        resolved_trade_dates: list[str] | None = None,
        full_day_suspend_dates: set[str] | list[str] | None = None,
    ) -> list[str]:
        """检查单股区间复权因子完整性，缺日写 log 并按连续区间补拉。"""
        return self._check_complete_by_ts_code(
            self._resolve_spec("adj_factor"),
            ts_code=ts_code, list_date=list_date, delist_date=delist_date,
            start_date=start_date, end_date=end_date,
            open_trade_dates=open_trade_dates,
            resolved_trade_dates=resolved_trade_dates,
            full_day_suspend_dates=full_day_suspend_dates,
        )

    def check_kline_stk_limit_complete_by_ts_code(
        self,
        *,
        ts_code: str,
        list_date: str | None,
        delist_date: str | None,
        start_date: str,
        end_date: str,
        open_trade_dates: list[str] | None = None,
        resolved_trade_dates: list[str] | None = None,
        full_day_suspend_dates: set[str] | list[str] | None = None,
    ) -> list[str]:
        """检查单股区间涨跌停价完整性，缺日写 log 并按连续区间补拉。"""
        return self._check_complete_by_ts_code(
            self._resolve_spec("stk_limit"),
            ts_code=ts_code, list_date=list_date, delist_date=delist_date,
            start_date=start_date, end_date=end_date,
            open_trade_dates=open_trade_dates,
            resolved_trade_dates=resolved_trade_dates,
            full_day_suspend_dates=full_day_suspend_dates,
        )

    # ---------- period_count ----------

    def build_kline_daily_period_count_rows(
        self, start_date: str, end_date: str
    ) -> list[dict[str, int | str]]:
        """聚合 kline_daily_period_count 行（不落库）。"""
        if not start_date or not end_date or start_date > end_date:
            return []

        trade_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=start_date, end_date=end_date, exchange="SSE",
        )
        if not trade_dates:
            return []

        kline_rows = self.local_kline_extract.get_trade_date_list(
            start_date=start_date, end_date=end_date,
        )
        kline_by_date = {r["trade_date"]: r for r in kline_rows}
        adj_rows = self.kline_daily_service.list_trade_date_adj_factor_counts(
            start_date=start_date, end_date=end_date,
        )
        adj_by_date = {r["trade_date"]: r for r in adj_rows}
        limit_rows = self.kline_daily_service.list_trade_date_stk_limit_counts(
            start_date=start_date, end_date=end_date,
        )
        limit_by_date = {r["trade_date"]: r for r in limit_rows}
        stock_counts = self.active_count_service.resolve_trading_counts(trade_dates)

        return [
            {
                "trade_date": td,
                "period_stock_count": int(stock_counts.get(td, 0)),
                "kline_daily_count": int(
                    kline_by_date.get(td, {}).get("kline_daily_count") or 0
                ),
                "kline_adj_factor_count": int(
                    adj_by_date.get(td, {}).get("kline_adj_factor_count") or 0
                ),
                "kline_stk_limit_count": int(
                    limit_by_date.get(td, {}).get("kline_stk_limit_count") or 0
                ),
            }
            for td in trade_dates
        ]

    def kline_daily_period_count(self, start_date: str, end_date: str) -> int:
        """聚合并落库 kline_daily_period_count。"""
        merged = self.build_kline_daily_period_count_rows(start_date, end_date)
        if not merged:
            return 0
        return self.kline_load.load_kline_daily_period_count(merged)

    def load_kline_daily_period_count_rows(
        self, merged: list[dict[str, int | str]]
    ) -> int:
        """将已聚合的 kline_daily_period_count 行 upsert 落库。"""
        if not merged:
            return 0
        return self.kline_load.load_kline_daily_period_count(merged)
