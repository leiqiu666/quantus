"""停复牌 Extract：调 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.stock.stock_suspend_tushare_client import TushareSuspendClient


class SuspendExtract:
    def __init__(self) -> None:
        self._client = TushareSuspendClient()

    def pull_suspend_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._client.pull_suspend_by_date(trade_date)
