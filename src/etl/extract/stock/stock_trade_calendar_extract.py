"""交易日历 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.stock.stock_trade_calendar_common import is_usable_trade_cal
from src.etl.client.stock.stock_trade_calendar_tushare_client import TushareTradeCalClient


class TradeCalExtract:
    def __init__(self) -> None:
        self._client = TushareTradeCalClient()

    def pull_trade_cal_range(
        self,
        *,
        exchange: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        df = self._client.pull_trade_cal_range(
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )
        if not is_usable_trade_cal(df):
            return pd.DataFrame()
        return df
