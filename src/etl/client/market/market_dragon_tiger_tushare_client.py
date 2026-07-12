"""Tushare 龙虎榜 Client（top_list + top_inst）。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.market.market_dragon_tiger_common import (
    TOP_LIST_COLUMNS,
    TOP_INST_COLUMNS,
    finalize_top_list,
    finalize_top_inst,
)

_acquire_rate_limit = create_rate_limiter(200)


class TushareDragonTigerClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_top_list_by_date(self, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_rate_limit()
        df = call_with_network_retry(
            self.ts.top_list,
            trade_date=td,
            fields=",".join(TOP_LIST_COLUMNS),
        )
        return finalize_top_list(df)

    def pull_top_inst_by_date(self, trade_date: str) -> pd.DataFrame:
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        _acquire_rate_limit()
        df = call_with_network_retry(
            self.ts.top_inst,
            trade_date=td,
            fields=",".join(TOP_INST_COLUMNS),
        )
        return finalize_top_inst(df)
