"""Tushare 停复牌 Client（suspend_d）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.base import call_with_network_retry
from src.etl.client.stock.stock_suspend_common import finalize_suspend

_acquire_suspend_rate_limit = create_rate_limiter(200)


class TushareSuspendClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_suspend_by_date(self, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_suspend_rate_limit()
        df = call_with_network_retry(
            self.ts.suspend_d,
            trade_date=td,
            fields=",".join(tushare_entities.suspend_d),
        )
        return finalize_suspend(df)
