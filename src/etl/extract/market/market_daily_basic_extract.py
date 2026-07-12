"""每日基本面指标 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_daily_basic_tushare_client import TushareDailyBasicClient


class DailyBasicExtract:
    def __init__(self) -> None:
        self._client = TushareDailyBasicClient()

    def pull_daily_basic_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_daily_basic_by_date(trade_date=trade_date)
