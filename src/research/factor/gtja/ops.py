"""国泰 191 常用算子（Polars Series，按 ts_code 分组）。"""

from __future__ import annotations

import math
from typing import Any

import polars as pl


def _as_series(x: Any, ref: pl.Series) -> pl.Series:
    if isinstance(x, pl.Series):
        return x.cast(pl.Float64)
    if isinstance(x, bool):
        return pl.Series([1.0 if x else 0.0] * ref.len())
    if isinstance(x, (int, float)):
        return pl.Series([float(x)] * ref.len())
    raise TypeError(f"不支持的算子输入类型: {type(x)}")


class OpsContext:
    def __init__(self, df: pl.DataFrame) -> None:
        self.df = df
        self.ts_code = df["ts_code"]
        self.n = df.height

    def const(self, v: float | int | bool) -> pl.Series:
        return _as_series(v, self.ts_code)

    def _with(self, s: pl.Series, expr: pl.Expr) -> pl.Series:
        return (
            pl.DataFrame({"ts_code": self.ts_code, "x": s})
            .with_columns(expr.alias("y"))
            ["y"]
        )

    def DELAY(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return self._with(s, pl.col("x").shift(int(d)).over("ts_code"))

    def DELTA(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return s - self.DELAY(s, int(d))

    def SUM(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return self._with(
            s, pl.col("x").rolling_sum(window_size=int(d)).over("ts_code")
        )

    def MEAN(self, x: Any, d: Any = None) -> pl.Series:
        s = _as_series(x, self.ts_code)
        if d is None:
            return (
                pl.DataFrame({"trade_date": self.df["trade_date"], "x": s})
                .with_columns(pl.col("x").mean().over("trade_date").alias("y"))
                ["y"]
            )
        # MEAN(x, d) 时序；若误传 Series 则取标量窗口失败时退回截面
        if isinstance(d, pl.Series):
            return (
                pl.DataFrame({"trade_date": self.df["trade_date"], "x": s})
                .with_columns(pl.col("x").mean().over("trade_date").alias("y"))
                ["y"]
            )
        return self._with(
            s, pl.col("x").rolling_mean(window_size=int(d)).over("ts_code")
        )

    def STD(self, x: Any, d: int) -> pl.Series:
        # 兼容 STD(CLOSE:20) 被清洗成异常的情况：第二参必须是 int
        s = _as_series(x, self.ts_code)
        return self._with(
            s, pl.col("x").rolling_std(window_size=int(d)).over("ts_code")
        )

    def SMA(self, x: Any, n: int, m: int = 1) -> pl.Series:
        s = _as_series(x, self.ts_code)
        alpha = float(m) / float(n)
        return self._with(
            s,
            pl.col("x")
            .ewm_mean(alpha=alpha, adjust=False, ignore_nulls=True)
            .over("ts_code"),
        )

    def WMA(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        d = int(d)
        weights = list(range(1, d + 1))
        wsum = float(sum(weights))

        def _one_group(arr: list[float | None]) -> list[float | None]:
            out: list[float | None] = [None] * len(arr)
            for i in range(d - 1, len(arr)):
                window = arr[i - d + 1 : i + 1]
                if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in window):
                    continue
                out[i] = sum(float(v) * w for v, w in zip(window, weights)) / wsum
            return out

        parts = []
        for _, g in pl.DataFrame({"ts_code": self.ts_code, "x": s}).group_by(
            "ts_code", maintain_order=True
        ):
            parts.append(pl.Series(_one_group(g["x"].to_list())))
        return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

    def TSMAX(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return self._with(
            s, pl.col("x").rolling_max(window_size=int(d)).over("ts_code")
        )

    def TSMIN(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return self._with(
            s, pl.col("x").rolling_min(window_size=int(d)).over("ts_code")
        )

    def MAX(self, a: Any, b: Any = None) -> pl.Series:
        # MAX(series, int) → TSMAX；MAX(a,b) 逐元素
        if b is None:
            return _as_series(a, self.ts_code)
        if isinstance(b, (int, float)) and isinstance(a, pl.Series):
            return self.TSMAX(a, int(b))
        if isinstance(a, (int, float)) and isinstance(b, pl.Series):
            return self.TSMAX(b, int(a))
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return self.const(max(float(a), float(b)))
        sa, sb = _as_series(a, self.ts_code), _as_series(b, self.ts_code)
        return (
            pl.DataFrame({"a": sa, "b": sb})
            .select(pl.max_horizontal("a", "b"))
            .to_series()
        )

    def MIN(self, a: Any, b: Any = None) -> pl.Series:
        if b is None:
            return _as_series(a, self.ts_code)
        if isinstance(b, (int, float)) and isinstance(a, pl.Series):
            return self.TSMIN(a, int(b))
        if isinstance(a, (int, float)) and isinstance(b, pl.Series):
            return self.TSMIN(b, int(a))
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return self.const(min(float(a), float(b)))
        sa, sb = _as_series(a, self.ts_code), _as_series(b, self.ts_code)
        return (
            pl.DataFrame({"a": sa, "b": sb})
            .select(pl.min_horizontal("a", "b"))
            .to_series()
        )

    def ABS(self, x: Any) -> pl.Series:
        return _as_series(x, self.ts_code).abs()

    def SIGN(self, x: Any) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return (
            pl.DataFrame({"x": s})
            .select(
                pl.when(pl.col("x") > 0)
                .then(1.0)
                .when(pl.col("x") < 0)
                .then(-1.0)
                .otherwise(0.0)
                .alias("y")
            )["y"]
        )

    def LOG(self, x: Any) -> pl.Series:
        return _as_series(x, self.ts_code).log()

    def RANK(self, x: Any, d: Any = None) -> pl.Series:
        # RANK(x, d) 在部分公式里实为时序分位 → TSRANK
        if d is not None and not isinstance(d, pl.Series):
            return self.TSRANK(x, int(d))
        s = _as_series(x, self.ts_code)
        return (
            pl.DataFrame({"trade_date": self.df["trade_date"], "x": s})
            .with_columns(
                (
                    pl.col("x").rank(method="average").over("trade_date")
                    / pl.col("x").count().over("trade_date")
                ).alias("r")
            )["r"]
        )

    def TSRANK(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        d = int(d)

        def _one(arr: list[float | None]) -> list[float | None]:
            out: list[float | None] = [None] * len(arr)
            for i in range(d - 1, len(arr)):
                window = arr[i - d + 1 : i + 1]
                cur = window[-1]
                if cur is None or (isinstance(cur, float) and math.isnan(cur)):
                    continue
                valid = [v for v in window if v is not None and not (isinstance(v, float) and math.isnan(v))]
                if not valid:
                    continue
                out[i] = sum(1 for v in valid if v <= cur) / float(len(valid))
            return out

        parts = []
        for _, g in pl.DataFrame({"ts_code": self.ts_code, "x": s}).group_by(
            "ts_code", maintain_order=True
        ):
            parts.append(pl.Series(_one(g["x"].to_list())))
        return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

    def CORR(self, x: Any, y: Any, d: int = 0) -> pl.Series:
        # CORR(a,b) 无窗口时默认 6（国泰部分公式省略）
        d = int(d) if d else 6
        sx, sy = _as_series(x, self.ts_code), _as_series(y, self.ts_code)
        return (
            pl.DataFrame({"ts_code": self.ts_code, "x": sx, "y": sy})
            .with_columns(
                pl.rolling_corr(pl.col("x"), pl.col("y"), window_size=d)
                .over("ts_code")
                .alias("c")
            )["c"]
        )

    def COVIANCE(self, x: Any, y: Any, d: int) -> pl.Series:
        sx, sy = _as_series(x, self.ts_code), _as_series(y, self.ts_code)
        return (
            pl.DataFrame({"ts_code": self.ts_code, "x": sx, "y": sy})
            .with_columns(
                pl.rolling_cov(pl.col("x"), pl.col("y"), window_size=int(d))
                .over("ts_code")
                .alias("c")
            )["c"]
        )

    def COVARIANCE(self, x: Any, y: Any, d: int) -> pl.Series:
        return self.COVIANCE(x, y, d)

    def COUNT(self, cond: Any, d: int) -> pl.Series:
        s = _as_series(cond, self.ts_code)
        # bool/条件转 0/1
        s = (s != 0).cast(pl.Float64)
        return self.SUM(s, int(d))

    def SUMIF(self, x: Any, d: int, cond: Any) -> pl.Series:
        sx = _as_series(x, self.ts_code)
        sc = _as_series(cond, self.ts_code)
        masked = (
            pl.DataFrame({"x": sx, "c": sc})
            .select(pl.when(pl.col("c") != 0).then(pl.col("x")).otherwise(0.0))
            .to_series()
        )
        return self.SUM(masked, int(d))

    def HIGHDAY(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        d = int(d)

        def _one(arr: list[float | None]) -> list[float | None]:
            out: list[float | None] = [None] * len(arr)
            for i in range(d - 1, len(arr)):
                window = arr[i - d + 1 : i + 1]
                if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in window):
                    continue
                mx = max(window)  # type: ignore[type-var]
                pos = len(window) - 1 - list(reversed(window)).index(mx)
                out[i] = float(len(window) - 1 - pos)
            return out

        parts = []
        for _, g in pl.DataFrame({"ts_code": self.ts_code, "x": s}).group_by(
            "ts_code", maintain_order=True
        ):
            parts.append(pl.Series(_one(g["x"].to_list())))
        return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

    def LOWDAY(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        d = int(d)

        def _one(arr: list[float | None]) -> list[float | None]:
            out: list[float | None] = [None] * len(arr)
            for i in range(d - 1, len(arr)):
                window = arr[i - d + 1 : i + 1]
                if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in window):
                    continue
                mn = min(window)  # type: ignore[type-var]
                pos = len(window) - 1 - list(reversed(window)).index(mn)
                out[i] = float(len(window) - 1 - pos)
            return out

        parts = []
        for _, g in pl.DataFrame({"ts_code": self.ts_code, "x": s}).group_by(
            "ts_code", maintain_order=True
        ):
            parts.append(pl.Series(_one(g["x"].to_list())))
        return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

    def DECAYLINEAR(self, x: Any, d: int) -> pl.Series:
        return self.WMA(x, int(d))

    def SEQUENCE(self, n: int) -> int:
        return int(n)

    def REGBETA(self, y: Any, x: Any, d: Any = None) -> pl.Series:
        sy = _as_series(y, self.ts_code)
        # REGBETA(y, n) → 对 SEQUENCE(n) 回归；REGBETA(y, x, n) → y 对 x 滚动回归
        if isinstance(x, pl.Series) or (d is not None and isinstance(d, (int, float))):
            sx = _as_series(x, self.ts_code)
            win = int(d) if d is not None else 20

            def _one_xy(ys: list[float | None], xs: list[float | None]) -> list[float | None]:
                out: list[float | None] = [None] * len(ys)
                for i in range(win - 1, len(ys)):
                    yw = ys[i - win + 1 : i + 1]
                    xw = xs[i - win + 1 : i + 1]
                    pairs = [
                        (float(a), float(b))
                        for a, b in zip(yw, xw)
                        if a is not None
                        and b is not None
                        and not (isinstance(a, float) and math.isnan(a))
                        and not (isinstance(b, float) and math.isnan(b))
                    ]
                    if len(pairs) < max(3, win // 2):
                        continue
                    mean_x = sum(p[1] for p in pairs) / len(pairs)
                    mean_y = sum(p[0] for p in pairs) / len(pairs)
                    var_x = sum((p[1] - mean_x) ** 2 for p in pairs)
                    if var_x == 0:
                        continue
                    cov = sum((p[1] - mean_x) * (p[0] - mean_y) for p in pairs)
                    out[i] = cov / var_x
                return out

            parts = []
            for _, g in pl.DataFrame(
                {"ts_code": self.ts_code, "y": sy, "x": sx}
            ).group_by("ts_code", maintain_order=True):
                parts.append(pl.Series(_one_xy(g["y"].to_list(), g["x"].to_list())))
            return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

        d = int(x) if isinstance(x, (int, float)) else 20
        seq = list(range(1, d + 1))
        mean_x = sum(seq) / d
        var_x = sum((v - mean_x) ** 2 for v in seq) or 1.0

        def _one(arr: list[float | None]) -> list[float | None]:
            out: list[float | None] = [None] * len(arr)
            for i in range(d - 1, len(arr)):
                window = arr[i - d + 1 : i + 1]
                if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in window):
                    continue
                mean_y = sum(float(v) for v in window) / d
                cov = sum((seq[j] - mean_x) * (float(window[j]) - mean_y) for j in range(d))
                out[i] = cov / var_x
            return out

        parts = []
        for _, g in pl.DataFrame({"ts_code": self.ts_code, "x": sy}).group_by(
            "ts_code", maintain_order=True
        ):
            parts.append(pl.Series(_one(g["x"].to_list())))
        return pl.concat(parts) if parts else pl.Series([], dtype=pl.Float64)

    def PROD(self, x: Any, d: int) -> pl.Series:
        s = _as_series(x, self.ts_code)
        return self._with(
            s,
            pl.col("x").log().rolling_sum(window_size=int(d)).exp().over("ts_code"),
        )

    def SUMAC(self, x: Any, d: int | None = None) -> pl.Series:
        s = _as_series(x, self.ts_code)
        if d is None:
            return self._with(s, pl.col("x").cum_sum().over("ts_code"))
        return self.SUM(s, int(d))

    def FILTER(self, x: Any, cond: Any) -> pl.Series:
        sx = _as_series(x, self.ts_code)
        sc = _as_series(cond, self.ts_code)
        return (
            pl.DataFrame({"x": sx, "c": sc})
            .select(pl.when(pl.col("c") != 0).then(pl.col("x")).otherwise(None))
            .to_series()
        )
