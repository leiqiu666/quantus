"""K 线 Client 统一接口。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class NotSupportedError(Exception):
    """当前数据源不支持该数据类型的拉取。"""


class KlineClientProtocol(Protocol):
    def pull_kline_daily_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame: ...

    def pull_kline_adj_factor_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame: ...

    def pull_kline_daily_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame: ...

    def pull_kline_adj_factor_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame: ...

    def pull_kline_stk_limit_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame: ...

    def pull_kline_stk_limit_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame: ...
