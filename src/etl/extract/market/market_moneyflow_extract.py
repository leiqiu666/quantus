"""个股资金流向 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_moneyflow_tushare_client import TushareMoneyflowClient


class MoneyflowExtract:
    def __init__(self) -> None:
        self._client = TushareMoneyflowClient()

    def pull_moneyflow_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_moneyflow_by_date(trade_date=trade_date)
