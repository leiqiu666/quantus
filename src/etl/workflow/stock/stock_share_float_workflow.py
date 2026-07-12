"""限售股解禁 Workflow：单日 Extract→Load 串联（按解禁日）。"""

from __future__ import annotations

from src.etl.extract.stock.stock_share_float_extract import StockShareFloatExtract
from src.etl.load.stock.stock_share_float_load import StockShareFloatLoad


class StockShareFloatWorkflow:
    def __init__(self) -> None:
        self.share_float_extract = StockShareFloatExtract()
        self.share_float_load = StockShareFloatLoad()

    def pull_share_float_by_float_date(self, *, float_date: str) -> int:
        df = self.share_float_extract.pull_share_float_by_float_date(float_date=float_date)
        return self.share_float_load.load_share_float(df)
