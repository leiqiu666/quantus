"""日 K Parquet 数据访问 → Polars LazyFrame。"""

from __future__ import annotations

import math
import re
from pathlib import Path

import polars as pl

from src.common.setting import settings


def _prev_months(year_month: str, n: int) -> list[str]:
    """返回 year_month 前 n 个月的 YYYYMM 列表（不含 year_month 本身，降序）。"""
    y, m = int(year_month[:4]), int(year_month[4:])
    result = []
    for _ in range(n):
        m -= 1
        if m < 1:
            y -= 1
            m = 12
        result.append(f"{y:04d}{m:02d}")
    return result


class KlineDataset:
    def __init__(self, warehouse_root: str | None = None) -> None:
        self._root = Path(warehouse_root or settings.warehouse_root)
        self._kline_dir = self._root / "kline_daily"

    def list_available_months(self) -> list[str]:
        if not self._kline_dir.exists():
            return []
        months = []
        for d in self._kline_dir.iterdir():
            if d.is_dir() and d.name.startswith("dt="):
                ym = d.name[3:]
                if re.fullmatch(r"\d{6}", ym):
                    months.append(ym)
        return sorted(months)

    def _parquet_glob(self, year_month: str) -> str:
        return str(self._kline_dir / f"dt={year_month}" / "*.parquet")

    def read_month(self, year_month: str) -> pl.LazyFrame:
        return pl.scan_parquet(self._parquet_glob(year_month))

    def read_months(self, months: list[str]) -> pl.LazyFrame:
        if not months:
            raise ValueError("months 不能为空")
        globs = [self._parquet_glob(ym) for ym in months]
        return pl.scan_parquet(globs)

    def read_month_with_window(
        self, year_month: str, window_days: int
    ) -> pl.LazyFrame:
        """
        读当月 + 前 N 个交易日的数据。

        window_days=0 → 只读当月。
        window_days>0 → 多读 ceil(window_days/21)+1 个月兜底。
        返回的 LazyFrame 增加 close_adj = close * adj_factor。
        """
        months_to_read = [year_month]
        if window_days > 0:
            extra = math.ceil(window_days / 21) + 1
            prev = _prev_months(year_month, extra)
            available = set(self.list_available_months())
            months_to_read = sorted(
                [ym for ym in prev if ym in available] + [year_month]
            )

        lf = self.read_months(months_to_read)
        return self._with_adj_columns(lf)

    def read_range(
        self,
        start: str,
        end: str,
        ts_codes: list[str] | None = None,
    ) -> pl.LazyFrame:
        """读 [start, end] 闭区间日 K，并附加后复权 OHLC 列。"""
        start = (start or "").strip()
        end = (end or "").strip()
        if not start or not end or start > end:
            raise ValueError(f"无效日期区间: {start!r} ~ {end!r}")

        s_ym, e_ym = start[:6], end[:6]
        available = self.list_available_months()
        months = [m for m in available if s_ym <= m <= e_ym]
        if not months:
            raise FileNotFoundError(f"无日 K 分区覆盖 {start}~{end}")

        lf = self.read_months(months)
        lf = lf.filter(
            (pl.col("trade_date") >= start) & (pl.col("trade_date") <= end)
        )
        if ts_codes is not None:
            lf = lf.filter(pl.col("ts_code").is_in(ts_codes))
        return self._with_adj_columns(lf)

    @staticmethod
    def _with_adj_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
        adj = pl.col("adj_factor").fill_null(1.0)
        return lf.with_columns(
            (pl.col("open") * adj).alias("open_adj"),
            (pl.col("high") * adj).alias("high_adj"),
            (pl.col("low") * adj).alias("low_adj"),
            (pl.col("close") * adj).alias("close_adj"),
        )
