"""Tushare 分红送股 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_dividend_common import DIVIDEND_COLUMNS, finalize_dividend

_acquire_dividend_rate_limit = create_rate_limiter(200)


class TushareDividendClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_dividend_by_record_date(self, *, record_date: str) -> pd.DataFrame:
        """按股权登记日拉取全市场分红记录。"""
        rd = (record_date or "").strip()
        if not rd:
            return pd.DataFrame()

        _acquire_dividend_rate_limit()
        df = call_with_network_retry(
            self.ts.dividend,
            record_date=rd,
            fields=list(DIVIDEND_COLUMNS),
        )
        return finalize_dividend(df)
