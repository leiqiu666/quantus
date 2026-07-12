"""Tushare 沪深港股通持股明细 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_hk_hold_common import HK_HOLD_COLUMNS, finalize_hk_hold

_acquire_hk_hold_rate_limit = create_rate_limiter(200)


class TushareHkHoldClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_hk_hold_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_hk_hold_rate_limit()
        df = call_with_network_retry(
            self.ts.hk_hold,
            trade_date=td,
            fields=",".join(HK_HOLD_COLUMNS),
        )
        return finalize_hk_hold(df)
