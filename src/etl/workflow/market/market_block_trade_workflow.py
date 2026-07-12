"""大宗交易 单日工作流：Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_block_trade_extract import BlockTradeExtract
from src.etl.load.market.market_block_trade_load import BlockTradeLoad


class BlockTradeWorkflow:
    def __init__(self) -> None:
        self.block_trade_extract = BlockTradeExtract()
        self.block_trade_load = BlockTradeLoad()

    def pull_block_trade_by_date(self, trade_date: str) -> int:
        df = self.block_trade_extract.pull_block_trade_by_date(trade_date)
        return self.block_trade_load.load_block_trade(df)
