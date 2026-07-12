"""指数基本信息 Workflow。"""

from __future__ import annotations

from src.etl.extract.index.index_basic_extract import IndexBasicExtract
from src.etl.load.index.index_basic_load import IndexBasicLoad


class IndexBasicWorkflow:
    def __init__(self) -> None:
        self.extract = IndexBasicExtract()
        self.load = IndexBasicLoad()

    def pull_index_basic_snapshot(self) -> int:
        df = self.extract.pull_index_basic_snapshot()
        return self.load.load_index_basic(df)
