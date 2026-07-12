"""量价因子：60 日波动率。"""

from __future__ import annotations

import polars as pl

from src.research.factor.base import BaseFactor, FactorMeta


class Volatility60d(BaseFactor):
    def meta(self) -> FactorMeta:
        return FactorMeta(
            name="volatility_60d",
            display_name="60日波动率",
            category="price_volume",
            frequency="daily",
            dependencies=("kline_daily",),
            params={"window": 60},
        )

    def compute(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        return (
            lf.sort("ts_code", "trade_date")
            .with_columns(
                (pl.col("close_adj") / pl.col("close_adj").shift(1).over("ts_code") - 1)
                .alias("daily_ret")
            )
            .with_columns(
                pl.col("daily_ret")
                .rolling_std(window_size=60, min_samples=30)
                .over("ts_code")
                .alias("value")
            )
            .select("ts_code", "trade_date", "value")
            .drop_nulls("value")
        )
