"""国泰 191 常用算子（Polars Series，按 ts_code 分组）。"""

from __future__ import annotations

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
        """加权移动平均：窗口内权重 1..d（越新越大），纯 Polars 滞后求和。"""
        s = _as_series(x, self.ts_code)
        d = int(d)
        if d <= 0:
            return s
        if d == 1:
            return s
        wsum = float(d * (d + 1) / 2)
        # lag k 对应权重 (d-k)：当前 k=0 权重 d，最旧 k=d-1 权重 1
        terms = [
            pl.col("x").shift(k).over("ts_code") * float(d - k) for k in range(d)
        ]
        return (
            pl.DataFrame({"ts_code": self.ts_code, "x": s})
            .with_columns((pl.sum_horizontal(terms) / wsum).alias("y"))
            ["y"]
        )

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

    def _apply_by_code_numpy(
        self,
        columns: dict[str, pl.Series],
        fn,
    ) -> pl.Series:
        """按 ts_code 分组，用 NumPy 数组调用 fn(**arrays) -> 1d array。"""
        import numpy as np

        frame_cols = {"ts_code": self.ts_code, **columns}
        df = pl.DataFrame(frame_cols)

        def _g(g: pl.DataFrame) -> pl.DataFrame:
            arrays = {k: g[k].to_numpy() for k in columns}
            out = fn(**arrays)
            if not isinstance(out, np.ndarray):
                out = np.asarray(out, dtype=np.float64)
            return pl.DataFrame({"y": out})

        return (
            df.group_by("ts_code", maintain_order=True)
            .map_groups(_g)
            ["y"]
        )

    def TSRANK(self, x: Any, d: int) -> pl.Series:
        import numpy as np

        s = _as_series(x, self.ts_code)
        d = int(d)

        def _fn(*, x: "np.ndarray") -> "np.ndarray":
            n = len(x)
            out = np.full(n, np.nan, dtype=np.float64)
            for i in range(d - 1, n):
                window = x[i - d + 1 : i + 1]
                cur = window[-1]
                if cur is None or (isinstance(cur, float) and np.isnan(cur)):
                    continue
                valid = window[np.isfinite(window.astype(float, copy=False))]
                if valid.size == 0:
                    continue
                out[i] = float(np.sum(valid <= float(cur)) / valid.size)
            return out

        return self._apply_by_code_numpy({"x": s}, _fn)

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
        import numpy as np

        s = _as_series(x, self.ts_code)
        d = int(d)

        def _fn(*, x: "np.ndarray") -> "np.ndarray":
            n = len(x)
            out = np.full(n, np.nan, dtype=np.float64)
            for i in range(d - 1, n):
                window = x[i - d + 1 : i + 1].astype(float, copy=False)
                if not np.isfinite(window).all():
                    continue
                pos = int(np.argmax(window))
                out[i] = float(d - 1 - pos)
            return out

        return self._apply_by_code_numpy({"x": s}, _fn)

    def LOWDAY(self, x: Any, d: int) -> pl.Series:
        import numpy as np

        s = _as_series(x, self.ts_code)
        d = int(d)

        def _fn(*, x: "np.ndarray") -> "np.ndarray":
            n = len(x)
            out = np.full(n, np.nan, dtype=np.float64)
            for i in range(d - 1, n):
                window = x[i - d + 1 : i + 1].astype(float, copy=False)
                if not np.isfinite(window).all():
                    continue
                pos = int(np.argmin(window))
                out[i] = float(d - 1 - pos)
            return out

        return self._apply_by_code_numpy({"x": s}, _fn)

    def DECAYLINEAR(self, x: Any, d: int) -> pl.Series:
        return self.WMA(x, int(d))

    def SEQUENCE(self, n: int) -> int:
        return int(n)

    def REGBETA(self, y: Any, x: Any, d: Any = None) -> pl.Series:
        import numpy as np

        sy = _as_series(y, self.ts_code)
        if isinstance(x, pl.Series) or (d is not None and isinstance(d, (int, float))):
            sx = _as_series(x, self.ts_code)
            win = int(d) if d is not None else 20

            def _fn(*, y: "np.ndarray", x: "np.ndarray") -> "np.ndarray":
                n = len(y)
                out = np.full(n, np.nan, dtype=np.float64)
                min_pts = max(3, win // 2)
                for i in range(win - 1, n):
                    yw = y[i - win + 1 : i + 1].astype(float, copy=False)
                    xw = x[i - win + 1 : i + 1].astype(float, copy=False)
                    mask = np.isfinite(yw) & np.isfinite(xw)
                    if int(mask.sum()) < min_pts:
                        continue
                    yy = yw[mask]
                    xx = xw[mask]
                    mean_x = float(xx.mean())
                    mean_y = float(yy.mean())
                    var_x = float(np.sum((xx - mean_x) ** 2))
                    if var_x == 0:
                        continue
                    cov = float(np.sum((xx - mean_x) * (yy - mean_y)))
                    out[i] = cov / var_x
                return out

            return self._apply_by_code_numpy({"y": sy, "x": sx}, _fn)

        d = int(x) if isinstance(x, (int, float)) else 20
        seq = np.arange(1, d + 1, dtype=np.float64)
        mean_x = float(seq.mean())
        var_x = float(np.sum((seq - mean_x) ** 2)) or 1.0

        def _fn_seq(*, x: "np.ndarray") -> "np.ndarray":
            n = len(x)
            out = np.full(n, np.nan, dtype=np.float64)
            for i in range(d - 1, n):
                window = x[i - d + 1 : i + 1].astype(float, copy=False)
                if not np.isfinite(window).all():
                    continue
                mean_y = float(window.mean())
                cov = float(np.sum((seq - mean_x) * (window - mean_y)))
                out[i] = cov / var_x
            return out

        return self._apply_by_code_numpy({"x": sy}, _fn_seq)

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
