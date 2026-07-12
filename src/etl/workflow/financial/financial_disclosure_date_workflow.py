"""财报披露计划 Workflow。"""

from __future__ import annotations

from src.etl.extract.financial.financial_disclosure_date_extract import DisclosureDateExtract
from src.etl.load.financial.financial_disclosure_date_load import DisclosureDateLoad


class DisclosureDateWorkflow:
    def __init__(self) -> None:
        self.extract = DisclosureDateExtract()
        self.load = DisclosureDateLoad()

    def pull_disclosure_date_by_period(self, period: str) -> int:
        df = self.extract.pull_disclosure_date_by_period(period)
        return self.load.load_disclosure_date(df)
