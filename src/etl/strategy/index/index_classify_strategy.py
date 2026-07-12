"""申万行业分类 Strategy。"""

from __future__ import annotations

import queue

from src.etl.workflow.index.index_classify_workflow import IndexClassifyWorkflow


class IndexClassifyStrategy:
    def __init__(self) -> None:
        self.workflow = IndexClassifyWorkflow()

    def pull_snapshot(self, *, progress_queue: queue.Queue | None = None) -> int:
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": 1})
        saved = self.workflow.pull_index_classify_snapshot()
        if progress_queue is not None:
            progress_queue.put({
                "index": 1,
                "total": 1,
                "period": "snapshot",
                "saved": saved,
            })
        return saved
