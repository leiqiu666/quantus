"""收益率绩效指标。"""

from __future__ import annotations

import math

import polars as pl


def calc_returns_metrics(daily_returns: list[float], *, periods_per_year: int = 252) -> dict:
    rets = [float(r) for r in daily_returns if r is not None]
    if not rets:
        return {
            "annual_return": None,
            "sharpe": None,
            "mdd": None,
            "calmar": None,
        }

    n = len(rets)
    wealth = 1.0
    peak = 1.0
    mdd = 0.0
    for r in rets:
        wealth *= 1.0 + r
        peak = max(peak, wealth)
        dd = wealth / peak - 1.0
        mdd = min(mdd, dd)

    total = wealth - 1.0
    annual = (1.0 + total) ** (periods_per_year / max(n, 1)) - 1.0 if n > 0 else None

    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / max(n - 1, 1)
    std = math.sqrt(var)
    sharpe = (mean / std) * math.sqrt(periods_per_year) if std > 0 else None
    calmar = (annual / abs(mdd)) if annual is not None and mdd < 0 else None

    return {
        "annual_return": annual,
        "sharpe": sharpe,
        "mdd": mdd,
        "calmar": calmar,
    }


def metrics_from_frame(df: pl.DataFrame, col: str) -> dict:
    if df.is_empty() or col not in df.columns:
        return calc_returns_metrics([])
    return calc_returns_metrics(df[col].to_list())
