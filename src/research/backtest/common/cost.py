"""回测成本模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """默认：佣金双边万三、印花税卖出千一、滑点 0。"""

    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    slippage_rate: float = 0.0

    def trade_cost(self, notional: float, *, is_sell: bool) -> float:
        """按成交金额绝对值计成本。"""
        n = abs(float(notional))
        if n <= 0:
            return 0.0
        cost = n * (self.commission_rate + self.slippage_rate)
        if is_sell:
            cost += n * self.stamp_duty_rate
        return cost

    def turnover_cost(self, buy_notional: float, sell_notional: float) -> float:
        return self.trade_cost(buy_notional, is_sell=False) + self.trade_cost(
            sell_notional, is_sell=True
        )
