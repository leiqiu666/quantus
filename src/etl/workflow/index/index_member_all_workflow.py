"""申万行业成分 Workflow。"""

from __future__ import annotations

from src.etl.extract.index.index_member_all_extract import IndexMemberAllExtract
from src.etl.load.index.index_member_all_load import IndexMemberAllLoad


class IndexMemberAllWorkflow:
    def __init__(self) -> None:
        self.extract = IndexMemberAllExtract()
        self.load = IndexMemberAllLoad()

    def pull_index_member_all_snapshot(self) -> int:
        df = self.extract.pull_index_member_all_snapshot()
        return self.load.load_index_member_all(df)
