"""龙虎榜 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_dragon_tiger_tushare_client import TushareDragonTigerClient


class DragonTigerExtract:
    def __init__(self) -> None:
        self._client = TushareDragonTigerClient()

    def pull_top_list_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._client.pull_top_list_by_date(trade_date)

    def pull_top_inst_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._client.pull_top_inst_by_date(trade_date)
