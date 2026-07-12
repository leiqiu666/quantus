"""分红送股 Workflow：单日 Extract→Load 串联。"""

from __future__ import annotations

from src.etl.extract.market.market_dividend_extract import DividendExtract
from src.etl.load.market.market_dividend_load import DividendLoad


class DividendWorkflow:
    def __init__(self) -> None:
        self.dividend_extract = DividendExtract()
        self.dividend_load = DividendLoad()

    def pull_dividend_by_record_date(self, *, record_date: str) -> int:
        df = self.dividend_extract.pull_dividend_by_record_date(record_date=record_date)
        return self.dividend_load.load_dividend(df)
