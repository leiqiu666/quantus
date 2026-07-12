"""主营业务构成 Workflow。"""

from __future__ import annotations

from src.etl.extract.financial.financial_fina_mainbz_extract import FinaMainbzExtract
from src.etl.load.financial.financial_fina_mainbz_load import FinaMainbzLoad


class FinaMainbzWorkflow:
    def __init__(self) -> None:
        self.extract = FinaMainbzExtract()
        self.load = FinaMainbzLoad()

    def pull_fina_mainbz_period(self, *, period: str) -> int:
        df = self.extract.pull_fina_mainbz_period(period)
        return self.load.load_fina_mainbz(df)
