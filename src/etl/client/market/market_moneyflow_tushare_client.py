"""Tushare 个股资金流向 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_moneyflow_common import MONEYFLOW_COLUMNS, finalize_moneyflow

_acquire_moneyflow_rate_limit = create_rate_limiter(500)


class TushareMoneyflowClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_moneyflow_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_moneyflow_rate_limit()
        df = call_with_network_retry(
            self.ts.moneyflow,
            trade_date=td,
            fields=",".join(MONEYFLOW_COLUMNS),
        )
        return finalize_moneyflow(df)
