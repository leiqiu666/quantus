"""前十大流通股东 Workflow：Extract→Load 串联（按公告日）。"""

from __future__ import annotations

from src.etl.extract.financial.financial_top10_floatholders_extract import Top10FloatholdersExtract
from src.etl.load.financial.financial_top10_floatholders_load import Top10FloatholdersLoad


class Top10FloatholdersWorkflow:
    def __init__(self) -> None:
        self.extract = Top10FloatholdersExtract()
        self.load = Top10FloatholdersLoad()

    def pull_top10_floatholders_by_ann_date(self, *, ann_date: str) -> int:
        df = self.extract.pull_top10_floatholders_by_ann_date(ann_date=ann_date)
        return self.load.load_top10_floatholders(df)
