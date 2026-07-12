"""大宗交易 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.market.market_block_trade_tushare_client import TushareBlockTradeClient


class BlockTradeExtract:
    def __init__(self) -> None:
        self._client = TushareBlockTradeClient()

    def pull_block_trade_by_date(self, trade_date: str) -> pd.DataFrame:
        return self._client.pull_block_trade_by_date(trade_date)
