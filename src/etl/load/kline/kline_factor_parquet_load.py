"""Tushare 技术因子 Parquet Load：宽表 unpivot → 按因子名分目录写入 factor/{name}/dt=YYYYMM/。"""

from __future__ import annotations

import uuid
from pathlib import Path

import polars as pl

from src.common.setting import settings
from src.etl.load.warehouse.warehouse_parquet_load import ParquetLoad

_FIXED_COLS = {"ts_code", "trade_date"}


class TushareFactorParquetLoad:
    def __init__(self) -> None:
        self._loader = ParquetLoad()
        self._root = Path(settings.warehouse_root)
        self._factor_root = self._root / "factor"

    def write_month_partition(self, df: pl.DataFrame, year_month: str) -> int:
        """把宽表 DataFrame 拆成 N 个因子，每个写一个长表 Parquet。"""
        if df.is_empty():
            return 0

        factor_cols = [c for c in df.columns if c not in _FIXED_COLS]
        total = 0

        for fname in factor_cols:
            long = (
                df.select("ts_code", "trade_date", pl.col(fname).alias("value"))
                .drop_nulls("value")
                .sort("trade_date", "ts_code")
            )
            if long.is_empty():
                continue

            partition_rel = f"factor/{fname}/dt={year_month}"
            self._loader.remove_partition(self._root, partition_rel)
            file_path = (
                self._factor_root / fname / f"dt={year_month}"
                / f"part-{uuid.uuid4().hex}.parquet"
            )
            rows = self._loader.write_table(long.to_arrow(), file_path)
            total += rows

        return total

    def read_existing_trade_dates(self) -> set[str]:
        """扫描所有 Tushare 因子目录中的 trade_date（取第一个因子作为代表）。"""
        if not self._factor_root.exists():
            return set()

        # 用 turnover_rate 作为代表（Tushare 因子一定有此列）
        probe = self._factor_root / "turnover_rate"
        if not probe.exists():
            return set()

        glob = str(probe / "**" / "*.parquet")
        try:
            dates = (
                pl.scan_parquet(glob)
                .select("trade_date")
                .unique()
                .collect()
                .to_series()
                .to_list()
            )
            return set(dates)
        except Exception:
            return set()
