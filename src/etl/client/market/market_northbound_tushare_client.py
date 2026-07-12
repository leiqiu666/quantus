"""Tushare 沪深股通十大成交股 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_northbound_common import HSGT_TOP10_COLUMNS, finalize_hsgt_top10

_acquire_hsgt_rate_limit = create_rate_limiter(500)


class TushareHsgtClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_hsgt_top10_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_hsgt_rate_limit()
        df = call_with_network_retry(
            self.ts.hsgt_top10,
            trade_date=td,
            fields=",".join(HSGT_TOP10_COLUMNS),
        )
        return finalize_hsgt_top10(df)
