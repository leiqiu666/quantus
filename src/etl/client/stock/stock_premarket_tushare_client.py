"""Tushare 盘前股本 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.base import call_with_network_retry
from src.etl.client.stock.stock_premarket_common import finalize_stock_premarket

_acquire_rate_limit = create_rate_limiter(500)


class TushareStockPremarketClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_premarket_by_date(self, *, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_rate_limit()
        df = call_with_network_retry(
            self.ts.stk_premarket,
            trade_date=td,
            fields=",".join(tushare_entities.stk_premarket),
        )
        return finalize_stock_premarket(df)
