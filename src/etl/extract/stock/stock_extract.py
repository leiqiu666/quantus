"""股票列表 Extract：编排数据源 Client（当前仅 Tushare）。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.stock.stock_tushare_client import TushareStockClient

# Tushare stock_basic list_status：默认仅 L，须显式拉齐四态
STOCK_BASIC_LIST_STATUSES = ("L", "D", "P", "G")


class StockExtract:
    def __init__(self) -> None:
        self._client = TushareStockClient()

    def pull_stock_list_a(self, **kwargs):
        return self._client.pull_stock_list_a(**kwargs)

    def pull_stock_list_a_all_statuses(self) -> pd.DataFrame:
        """
        按 L/D/P/G 分别调用 stock_basic，合并后按 ts_code 去重。

        Tushare 默认 list_status=L，单次拉取会缺失退市/暂停/未交易股票。
        """
        parts: list[pd.DataFrame] = []
        for status in STOCK_BASIC_LIST_STATUSES:
            df = self.pull_stock_list_a(list_status=status)
            if df is not None and not df.empty:
                parts.append(df)

        if not parts:
            return pd.DataFrame()

        merged = pd.concat(parts, ignore_index=True)
        if "ts_code" in merged.columns:
            merged = merged.drop_duplicates(subset=["ts_code"], keep="last")
        return merged
