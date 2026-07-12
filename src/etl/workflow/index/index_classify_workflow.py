"""申万行业分类 Workflow。"""

from __future__ import annotations

from src.etl.extract.index.index_classify_extract import IndexClassifyExtract
from src.etl.load.index.index_classify_load import IndexClassifyLoad


class IndexClassifyWorkflow:
    def __init__(self) -> None:
        self.extract = IndexClassifyExtract()
        self.load = IndexClassifyLoad()

    def pull_index_classify_snapshot(self) -> int:
        df = self.extract.pull_index_classify_snapshot()
        return self.load.load_index_classify(df)
