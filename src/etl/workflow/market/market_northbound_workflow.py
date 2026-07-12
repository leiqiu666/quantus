"""沪深股通十大成交股 Workflow。"""

from __future__ import annotations

from src.etl.extract.market.market_northbound_extract import HsgtExtract
from src.etl.load.market.market_northbound_load import HsgtLoad


class HsgtWorkflow:
    def __init__(self) -> None:
        self.hsgt_extract = HsgtExtract()
        self.hsgt_load = HsgtLoad()

    def pull_hsgt_top10_by_date(self, *, trade_date: str) -> int:
        df = self.hsgt_extract.pull_hsgt_top10_by_date(trade_date=trade_date)
        return self.hsgt_load.load_hsgt_top10(df)
