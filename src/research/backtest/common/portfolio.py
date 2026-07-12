"""组合权重与换手。"""

from __future__ import annotations

from src.research.backtest.common.cost import CostModel


def renormalize(weights: dict[str, float]) -> dict[str, float]:
    s = sum(abs(v) for v in weights.values())
    if s <= 0:
        return {}
    return {k: v / s for k, v in weights.items() if abs(v) > 0}


def filter_and_renorm(
    weights: dict[str, float],
    tradable: set[str],
) -> dict[str, float]:
    kept = {k: v for k, v in weights.items() if k in tradable}
    return renormalize(kept)


def turnover_and_cost(
    prev: dict[str, float],
    curr: dict[str, float],
    cost_model: CostModel,
) -> tuple[float, float, list[dict]]:
    """
    假设组合名义本金=1。
    返回 (turnover, cost, trades)。
    trades: trade_date 由调用方补；含 ts_code, delta_weight, cost
    """
    keys = set(prev) | set(curr)
    buy = 0.0
    sell = 0.0
    trades: list[dict] = []
    for k in keys:
        dw = curr.get(k, 0.0) - prev.get(k, 0.0)
        if abs(dw) < 1e-12:
            continue
        if dw > 0:
            buy += dw
            c = cost_model.trade_cost(dw, is_sell=False)
        else:
            sell += -dw
            c = cost_model.trade_cost(-dw, is_sell=True)
        trades.append({"ts_code": k, "delta_weight": dw, "cost": c})
    turnover = buy + sell
    total_cost = cost_model.turnover_cost(buy, sell)
    return turnover, total_cost, trades
