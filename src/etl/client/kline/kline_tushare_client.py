"""Tushare K 线 Client（daily、adj_factor、stk_limit）。

通过 ``_KLINE_DIMENSION_SPECS`` 三个维度共享同一份「分页 range / 按日全市场」实现，
每个维度只声明自己的 Tushare 方法名、单次最大行数、限流器与 finalize 函数。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.base import call_with_network_retry
from src.etl.client.kline.kline_common import (
    finalize_kline_adj_factor,
    finalize_kline_daily,
    finalize_kline_stk_limit,
)


@dataclass(frozen=True)
class _KlineDimensionSpec:
    name: str
    ts_method_name: str          # ts.daily / ts.adj_factor / ts.stk_limit
    fields_attr: str             # TushareKlineClient 实例上的 fields 属性名
    max_rows: int                # 单次返回上限（达到则需要向前分页）
    acquire_rate_limit: Callable[[], None]
    finalize: Callable[[pd.DataFrame], pd.DataFrame]


_KLINE_DIMENSION_SPECS: Dict[str, _KlineDimensionSpec] = {
    "daily": _KlineDimensionSpec(
        name="daily",
        ts_method_name="daily",
        fields_attr="daily_fields",
        max_rows=6000,
        acquire_rate_limit=create_rate_limiter(500),
        finalize=finalize_kline_daily,
    ),
    "adj_factor": _KlineDimensionSpec(
        name="adj_factor",
        ts_method_name="adj_factor",
        fields_attr="adj_factor_fields",
        max_rows=3000,
        acquire_rate_limit=create_rate_limiter(500),
        finalize=finalize_kline_adj_factor,
    ),
    "stk_limit": _KlineDimensionSpec(
        name="stk_limit",
        ts_method_name="stk_limit",
        fields_attr="stk_limit_fields",
        max_rows=5800,
        acquire_rate_limit=create_rate_limiter(500),
        finalize=finalize_kline_stk_limit,
    ),
}


def _ymd_sub_days(ymd: str, days: int = 1) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d")
    return (d - timedelta(days=days)).strftime("%Y%m%d")


def _normalize_trade_date(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else s


class TushareKlineClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
        self.daily_fields = tushare_entities.daily
        self.adj_factor_fields = tushare_entities.adj_factor
        self.stk_limit_fields = tushare_entities.stk_limit

    # ---------- 内部统一实现 ----------

    def _pull_one(
        self,
        spec: _KlineDimensionSpec,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """单次 Tushare 请求（已限流），仅返回 raw DataFrame，不调用 finalize。"""
        spec.acquire_rate_limit()
        ts_method = getattr(self.ts, spec.ts_method_name)
        df = call_with_network_retry(
            ts_method,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=getattr(self, spec.fields_attr),
        )
        if df is None:
            return pd.DataFrame()
        return df

    def _pull_range(
        self,
        spec: _KlineDimensionSpec,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """通用「向前分页」拉取：以 cur_end 不断左移至 start_date 为止。"""
        if not start_date or not end_date or start_date > end_date:
            return pd.DataFrame()

        parts: list[pd.DataFrame] = []
        cur_end = end_date

        while cur_end >= start_date:
            df = self._pull_one(
                spec,
                ts_code=ts_code,
                start_date=start_date,
                end_date=cur_end,
            )
            if df is None or df.empty:
                break

            parts.append(df)

            if len(df) < spec.max_rows:
                break
            if "trade_date" not in df.columns:
                break

            oldest = _normalize_trade_date(df["trade_date"].min())
            if not oldest or len(oldest) != 8:
                break

            next_end = _ymd_sub_days(oldest, 1)
            if next_end < start_date or next_end >= cur_end:
                break
            cur_end = next_end

        if not parts:
            return pd.DataFrame()

        out = pd.concat(parts, ignore_index=True)
        if "trade_date" in out.columns and "ts_code" in out.columns:
            out = out.drop_duplicates(subset=["ts_code", "trade_date"], keep="first")
        return spec.finalize(out)

    def _pull_by_trade_date(
        self,
        spec: _KlineDimensionSpec,
        *,
        trade_date: str,
    ) -> pd.DataFrame:
        """按交易日拉取全市场（一次请求即可）。"""
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        spec.acquire_rate_limit()
        ts_method = getattr(self.ts, spec.ts_method_name)
        df = call_with_network_retry(
            ts_method, trade_date=td, fields=getattr(self, spec.fields_attr)
        )
        return spec.finalize(df)

    # ---------- Protocol 公开 6 方法（薄壳） ----------

    def pull_kline_daily_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_range(
            _KLINE_DIMENSION_SPECS["daily"],
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def pull_kline_daily_by_trade_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_by_trade_date(
            _KLINE_DIMENSION_SPECS["daily"], trade_date=trade_date
        )

    def pull_kline_adj_factor_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_range(
            _KLINE_DIMENSION_SPECS["adj_factor"],
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def pull_kline_adj_factor_by_trade_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_by_trade_date(
            _KLINE_DIMENSION_SPECS["adj_factor"], trade_date=trade_date
        )

    def pull_kline_stk_limit_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_range(
            _KLINE_DIMENSION_SPECS["stk_limit"],
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def pull_kline_stk_limit_by_trade_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_by_trade_date(
            _KLINE_DIMENSION_SPECS["stk_limit"], trade_date=trade_date
        )
