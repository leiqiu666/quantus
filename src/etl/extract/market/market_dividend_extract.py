"""分红送股 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_dividend_tushare_client import TushareDividendClient


class DividendExtract:
    def __init__(self) -> None:
        self._client = TushareDividendClient()

    def pull_dividend_by_record_date(self, *, record_date: str) -> pd.DataFrame:
        return self._client.pull_dividend_by_record_date(record_date=record_date)
