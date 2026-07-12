"""前十大股东 单日工作流：Extract→Load 串联（按公告日）。"""

from __future__ import annotations

from src.etl.extract.financial.financial_shareholder_extract import ShareholderExtract
from src.etl.load.financial.financial_shareholder_load import ShareholderLoad


class ShareholderWorkflow:
    def __init__(self) -> None:
        self.shareholder_extract = ShareholderExtract()
        self.shareholder_load = ShareholderLoad()

    def pull_top10_by_ann_date(self, *, ann_date: str) -> int:
        df = self.shareholder_extract.pull_top10_by_ann_date(ann_date=ann_date)
        return self.shareholder_load.load_top10_holders(df)
