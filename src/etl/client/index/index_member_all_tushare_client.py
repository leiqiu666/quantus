"""Tushare 申万行业成分 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.index.index_member_all_common import (
    INDEX_MEMBER_ALL_COLUMNS,
    finalize_index_member_all,
)

_acquire_index_member_all_rate_limit = create_rate_limiter(200)


class TushareIndexMemberAllClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_index_member_all(
        self,
        *,
        l1_code: str | None = None,
        l2_code: str | None = None,
        l3_code: str | None = None,
        is_new: str = "Y",
    ) -> pd.DataFrame:
        kwargs: dict[str, str] = {"is_new": (is_new or "Y").strip() or "Y"}
        if (l1_code or "").strip():
            kwargs["l1_code"] = l1_code.strip()
        if (l2_code or "").strip():
            kwargs["l2_code"] = l2_code.strip()
        if (l3_code or "").strip():
            kwargs["l3_code"] = l3_code.strip()

        _acquire_index_member_all_rate_limit()
        df = call_with_network_retry(
            self.ts.index_member_all,
            fields=",".join(INDEX_MEMBER_ALL_COLUMNS),
            **kwargs,
        )
        return finalize_index_member_all(df)
