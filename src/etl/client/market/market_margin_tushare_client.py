"""Tushare 融资融券明细 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_margin_common import MARGIN_DETAIL_COLUMNS, finalize_margin_detail

_acquire_margin_rate_limit = create_rate_limiter(500)


class TushareMarginClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_margin_detail_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_margin_rate_limit()
        df = call_with_network_retry(
            self.ts.margin_detail,
            trade_date=td,
            fields=",".join(MARGIN_DETAIL_COLUMNS),
        )
        return finalize_margin_detail(df)
