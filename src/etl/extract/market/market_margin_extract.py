"""融资融券明细 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_margin_tushare_client import TushareMarginClient


class MarginExtract:
    def __init__(self) -> None:
        self._client = TushareMarginClient()

    def pull_margin_detail_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._client.pull_margin_detail_by_date(trade_date=trade_date)
