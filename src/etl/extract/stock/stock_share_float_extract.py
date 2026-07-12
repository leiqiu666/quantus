"""限售股解禁 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.stock.stock_share_float_tushare_client import TushareStockShareFloatClient


class StockShareFloatExtract:
    def __init__(self) -> None:
        self._client = TushareStockShareFloatClient()

    def pull_share_float_by_float_date(self, *, float_date: str) -> pd.DataFrame:
        return self._client.pull_share_float_by_float_date(float_date=float_date)
