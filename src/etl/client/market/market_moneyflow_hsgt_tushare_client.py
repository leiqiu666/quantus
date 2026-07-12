"""Tushare 沪深港通资金流向 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_moneyflow_hsgt_common import (
    MONEYFLOW_HSGT_COLUMNS,
    finalize_moneyflow_hsgt,
)

_acquire_moneyflow_hsgt_rate_limit = create_rate_limiter(500)


class TushareMoneyflowHsgtClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_moneyflow_hsgt_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_moneyflow_hsgt_rate_limit()
        df = call_with_network_retry(
            self.ts.moneyflow_hsgt,
            trade_date=td,
            fields=",".join(MONEYFLOW_HSGT_COLUMNS),
        )
        return finalize_moneyflow_hsgt(df)
