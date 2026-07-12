"""多因子截面：z-score 加权合成后再分组。"""

from __future__ import annotations

import math

import polars as pl

from src.research.strategy.single_factor import SingleFactorStrategy


class MultiFactorStrategy:
    """调仓日对各因子截面 z-score 加权求和，再按综合分分 n_groups。"""

    def __init__(
        self,
        items: list[tuple[str, float]],
        n_groups: int = 10,
        name: str = "multi_factor",
    ) -> None:
        cleaned: list[tuple[str, float]] = []
        for fname, w in items:
            fn = (fname or "").strip()
            if not fn:
                continue
            weight = float(w)
            if not math.isfinite(weight) or weight <= 0:
                continue
            cleaned.append((fn, weight))
        if len(cleaned) < 2:
            raise ValueError("多因子组合至少需要 2 个有效因子（正权重）")
        self.items = cleaned
        self.factor_name = name
        self.n_groups = max(int(n_groups), 2)
        self._inner = SingleFactorStrategy(name, n_groups=self.n_groups)

    @property
    def factor_names(self) -> list[str]:
        return [n for n, _ in self.items]

    def compose_scores(self, factor_cs: pl.DataFrame) -> pl.DataFrame:
        """返回 ts_code, value（综合分）。"""
        if factor_cs.is_empty() or "ts_code" not in factor_cs.columns:
            return pl.DataFrame(
                {"ts_code": pl.Series([], dtype=pl.Utf8), "value": pl.Series([], dtype=pl.Float64)}
            )

        df = factor_cs
        z_cols: list[str] = []
        weights: list[float] = []
        for fname, w in self.items:
            if fname not in df.columns:
                continue
            zname = f"_z_{fname}"
            series = df[fname]
            mean = series.mean()
            std = series.std()
            if mean is None or std is None or not math.isfinite(float(std)) or float(std) == 0.0:
                # 无波动或全空：有值处置 0，参与权重
                df = df.with_columns(
                    pl.when(pl.col(fname).is_not_null())
                    .then(0.0)
                    .otherwise(None)
                    .alias(zname)
                )
            else:
                m, s = float(mean), float(std)
                df = df.with_columns(
                    pl.when(pl.col(fname).is_null())
                    .then(None)
                    .otherwise((pl.col(fname) - m) / s)
                    .alias(zname)
                )
            z_cols.append(zname)
            weights.append(w)

        if not z_cols:
            return pl.DataFrame(
                {"ts_code": pl.Series([], dtype=pl.Utf8), "value": pl.Series([], dtype=pl.Float64)}
            )

        # 对有值因子加权并按有效权重归一
        weighted = None
        wsum = None
        for zc, w in zip(z_cols, weights):
            part = pl.when(pl.col(zc).is_not_null()).then(pl.col(zc) * w).otherwise(0.0)
            wpart = pl.when(pl.col(zc).is_not_null()).then(w).otherwise(0.0)
            weighted = part if weighted is None else (weighted + part)
            wsum = wpart if wsum is None else (wsum + wpart)

        assert weighted is not None and wsum is not None
        out = df.select(
            "ts_code",
            pl.when(wsum > 0)
            .then(weighted / wsum)
            .otherwise(None)
            .alias("value"),
        ).filter(pl.col("value").is_not_null())
        return out

    def target_weights(
        self,
        trade_date: str,
        factor_cs: pl.DataFrame,
        universe: list[str],
    ) -> dict[str, dict[str, float]]:
        composed = self.compose_scores(factor_cs)
        return self._inner.target_weights(trade_date, composed, universe)
