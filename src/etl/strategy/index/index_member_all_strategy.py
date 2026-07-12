"""申万行业成分 Strategy。"""

from __future__ import annotations

import queue

from src.etl.workflow.index.index_member_all_workflow import IndexMemberAllWorkflow


class IndexMemberAllStrategy:
    def __init__(self) -> None:
        self.workflow = IndexMemberAllWorkflow()

    def pull_snapshot(self, *, progress_queue: queue.Queue | None = None) -> int:
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": 1})
        saved = self.workflow.pull_index_member_all_snapshot()
        if progress_queue is not None:
            progress_queue.put({
                "index": 1,
                "total": 1,
                "period": "snapshot",
                "saved": saved,
            })
        return saved
