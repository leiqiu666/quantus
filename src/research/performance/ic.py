"""IC / RankIC。"""

from __future__ import annotations

import math

import polars as pl


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx <= 0 or dy <= 0:
        return None
    return num / (dx * dy)


def _rank(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(x: list[float], y: list[float]) -> float | None:
    return _pearson(_rank(x), _rank(y))


def calc_ic_row(
    factor_values: dict[str, float],
    forward_returns: dict[str, float],
) -> tuple[float | None, float | None]:
    keys = sorted(set(factor_values) & set(forward_returns))
    xs = [factor_values[k] for k in keys]
    ys = [forward_returns[k] for k in keys]
    return _pearson(xs, ys), _spearman(xs, ys)


def ic_summary(ic_series: pl.DataFrame) -> dict:
    if ic_series.is_empty() or "ic" not in ic_series.columns:
        return {"ic_mean": None, "rank_ic_mean": None, "icir": None}
    ic = [v for v in ic_series["ic"].to_list() if v is not None]
    ric = (
        [v for v in ic_series["rank_ic"].to_list() if v is not None]
        if "rank_ic" in ic_series.columns
        else []
    )
    def _mean(xs: list[float]) -> float | None:
        return sum(xs) / len(xs) if xs else None

    def _std(xs: list[float]) -> float | None:
        if len(xs) < 2:
            return None
        m = sum(xs) / len(xs)
        return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

    ic_mean = _mean(ic)
    ic_std = _std(ic)
    icir = (ic_mean / ic_std) if ic_mean is not None and ic_std and ic_std > 0 else None
    return {
        "ic_mean": ic_mean,
        "rank_ic_mean": _mean(ric),
        "icir": icir,
    }
