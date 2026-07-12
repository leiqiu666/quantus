"""因子计算 Workflow：单月 读数据 → compute → 裁剪 → 写 Parquet。"""

from __future__ import annotations

import polars as pl

from src.research.dataset.kline import KlineDataset
from src.research.factor.base import BaseFactor
from src.research.factor.load import FactorParquetLoad


class FactorComputeWorkflow:
    def __init__(self) -> None:
        self._dataset = KlineDataset()
        self._load = FactorParquetLoad()

    def compute_month(self, factor: BaseFactor, year_month: str) -> int:
        meta = factor.meta()

        lf = self._dataset.read_month_with_window(year_month, meta.window_size)

        result_lf = factor.compute(lf)

        ym_start = year_month + "01"
        ym_end = year_month + "31"
        result_lf = result_lf.filter(
            (pl.col("trade_date") >= ym_start) & (pl.col("trade_date") <= ym_end)
        )

        df = result_lf.sort("trade_date", "ts_code").collect()
        if df.is_empty():
            return 0

        table = df.to_arrow()
        return self._load.write_month_partition(table, meta.name, year_month)
