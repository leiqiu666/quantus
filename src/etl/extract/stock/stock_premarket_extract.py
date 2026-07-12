"""盘前股本 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.stock.stock_premarket_tushare_client import TushareStockPremarketClient


class StockPremarketExtract:
    def __init__(self) -> None:
        self._client = TushareStockPremarketClient()

    def pull_premarket_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_premarket_by_date(trade_date=trade_date)
