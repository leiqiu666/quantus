"""因子 Parquet 统一读取层（研究/回测权威入口）。"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from src.common.setting import settings


def _months_in_range(start: str, end: str) -> list[str]:
    """闭区间 [start, end]（YYYYMMDD）覆盖的 YYYYMM 列表。"""
    s, e = start[:6], end[:6]
    if not re.fullmatch(r"\d{6}", s) or not re.fullmatch(r"\d{6}", e) or s > e:
        return []
    y, m = int(s[:4]), int(s[4:])
    ey, em = int(e[:4]), int(e[4:])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


class FactorDataset:
    def __init__(self, warehouse_root: str | None = None) -> None:
        self._root = Path(warehouse_root or settings.warehouse_root)
        self._factor_dir = self._root / "factor"

    def list_factors(self) -> list[str]:
        if not self._factor_dir.exists():
            return []
        names = []
        for d in self._factor_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                names.append(d.name)
        return sorted(names)

    def list_available_months(self, factor_name: str) -> list[str]:
        fdir = self._factor_dir / factor_name
        if not fdir.exists():
            return []
        months = []
        for d in fdir.iterdir():
            if d.is_dir() and d.name.startswith("dt="):
                ym = d.name[3:]
                if re.fullmatch(r"\d{6}", ym):
                    months.append(ym)
        return sorted(months)

    def _globs_for_months(self, factor_name: str, months: list[str]) -> list[str]:
        fdir = self._factor_dir / factor_name
        globs = []
        for ym in months:
            pdir = fdir / f"dt={ym}"
            if pdir.exists():
                globs.append(str(pdir / "*.parquet"))
        return globs

    def read(
        self,
        factor_name: str,
        start: str,
        end: str,
        ts_codes: list[str] | None = None,
    ) -> pl.LazyFrame:
        start = (start or "").strip()
        end = (end or "").strip()
        if not factor_name or not start or not end or start > end:
            return pl.LazyFrame(
                schema={"ts_code": pl.Utf8, "trade_date": pl.Utf8, "value": pl.Float64}
            )

        months = _months_in_range(start, end)
        available = set(self.list_available_months(factor_name))
        months = [m for m in months if m in available]
        globs = self._globs_for_months(factor_name, months)
        if not globs:
            return pl.LazyFrame(
                schema={"ts_code": pl.Utf8, "trade_date": pl.Utf8, "value": pl.Float64}
            )

        lf = pl.scan_parquet(globs).select("ts_code", "trade_date", "value")
        lf = lf.filter(
            (pl.col("trade_date") >= start) & (pl.col("trade_date") <= end)
        )
        if ts_codes is not None:
            lf = lf.filter(pl.col("ts_code").is_in(ts_codes))
        return lf

    def read_multi(
        self,
        factor_names: list[str],
        trade_date: str,
    ) -> pl.DataFrame:
        trade_date = (trade_date or "").strip()
        if not factor_names or not trade_date:
            return pl.DataFrame({"ts_code": pl.Series([], dtype=pl.Utf8)})

        base_name = factor_names[0]
        base = (
            self.read(base_name, trade_date, trade_date)
            .select("ts_code", pl.col("value").alias(base_name))
            .collect()
        )
        if base.is_empty():
            cols = {"ts_code": pl.Series([], dtype=pl.Utf8)}
            for n in factor_names:
                cols[n] = pl.Series([], dtype=pl.Float64)
            return pl.DataFrame(cols)

        out = base
        for name in factor_names[1:]:
            other = (
                self.read(name, trade_date, trade_date)
                .select("ts_code", pl.col("value").alias(name))
                .collect()
            )
            if other.is_empty():
                out = out.with_columns(pl.lit(None).cast(pl.Float64).alias(name))
            else:
                out = out.join(other, on="ts_code", how="left")
        return out
