"""融资融券明细 Workflow。"""

from __future__ import annotations

from src.etl.extract.market.market_margin_extract import MarginExtract
from src.etl.load.market.market_margin_load import MarginLoad


class MarginWorkflow:
    def __init__(self) -> None:
        self.margin_extract = MarginExtract()
        self.margin_load = MarginLoad()

    def pull_margin_detail_by_date(self, *, trade_date: str) -> int:
        df = self.margin_extract.pull_margin_detail_by_date(trade_date=trade_date)
        return self.margin_load.load_margin_detail(df)
