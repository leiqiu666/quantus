"""沪深港通资金流向 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_moneyflow_hsgt_tushare_client import TushareMoneyflowHsgtClient


class MoneyflowHsgtExtract:
    def __init__(self) -> None:
        self._client = TushareMoneyflowHsgtClient()

    def pull_moneyflow_hsgt_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_moneyflow_hsgt_by_date(trade_date=trade_date)
