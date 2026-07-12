"""指数成分权重 Workflow。"""

from __future__ import annotations

from src.etl.extract.index.index_weight_extract import IndexWeightExtract
from src.etl.load.index.index_weight_load import IndexWeightLoad


class IndexWeightWorkflow:
    def __init__(self) -> None:
        self.extract = IndexWeightExtract()
        self.load = IndexWeightLoad()

    def pull_index_weight(
        self, *, index_code: str, start_date: str, end_date: str,
    ) -> int:
        df = self.extract.pull_index_weight(
            index_code=index_code, start_date=start_date, end_date=end_date,
        )
        return self.load.load_index_weight(df)
