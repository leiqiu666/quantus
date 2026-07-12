"""量价因子：20 日动量。"""

from __future__ import annotations

import polars as pl

from src.research.factor.base import BaseFactor, FactorMeta


class Momentum20d(BaseFactor):
    def meta(self) -> FactorMeta:
        return FactorMeta(
            name="momentum_20d",
            display_name="20日动量",
            category="price_volume",
            frequency="daily",
            dependencies=("kline_daily",),
            params={"window": 20},
        )

    def compute(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return (
            lf.sort("ts_code", "trade_date")
            .with_columns(
                (
                    pl.col("close_adj")
                    / pl.col("close_adj").shift(20).over("ts_code")
                    - 1
                ).alias("value")
            )
            .select("ts_code", "trade_date", "value")
            .drop_nulls("value")
        )
