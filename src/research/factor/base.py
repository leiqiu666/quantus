"""因子框架：BaseFactor 抽象类 + FactorMeta 元数据。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import polars as pl


@dataclass(frozen=True)
class FactorMeta:
    name: str
    display_name: str
    category: str
    frequency: str
    dependencies: tuple[str, ...]
    params: dict = field(default_factory=dict)
    version: int = 1

    @property
    def window_size(self) -> int:
        return self.params.get("window", 0)


class BaseFactor(ABC):
    @abstractmethod
    def meta(self) -> FactorMeta:
        """返回因子元数据。"""

    @abstractmethod
    def compute(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        纯计算，不管 IO。

        输入 lf 包含列：ts_code, trade_date, open, high, low, close, vol, amount,
                        adj_factor, up_limit, down_limit,
                        open_adj, high_adj, low_adj, close_adj（后复权）
        输出 lf 必须包含列：ts_code, trade_date, value
        """
