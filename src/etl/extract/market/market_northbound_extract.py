"""沪深股通十大成交股 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_northbound_tushare_client import TushareHsgtClient


class HsgtExtract:
    def __init__(self) -> None:
        self._client = TushareHsgtClient()

    def pull_hsgt_top10_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_hsgt_top10_by_date(trade_date=trade_date)
