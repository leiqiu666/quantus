"""盘前股本 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.stock.stock_premarket_extract import StockPremarketExtract
from src.etl.load.stock.stock_premarket_load import StockPremarketLoad


class StockPremarketWorkflow:
    def __init__(self) -> None:
        self.premarket_extract = StockPremarketExtract()
        self.premarket_load = StockPremarketLoad()

    def pull_premarket_by_date(self, *, trade_date: str) -> int:
        df = self.premarket_extract.pull_premarket_by_date(trade_date=trade_date)
        return self.premarket_load.load_premarket(df)
