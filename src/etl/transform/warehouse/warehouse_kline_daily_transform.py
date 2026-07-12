"""warehouse · 日 K Transform：DataFrame → Arrow Table。

不写 dt 列：dt 由 Hive 目录名 dt=YYYYMM 表达，读侧用 hive_partitioning=1 自动识别。
"""

from __future__ import annotations

import pandas as pd
import pyarrow as pa


_ARROW_SCHEMA = pa.schema(
    [
        ("ts_code", pa.string()),
        ("trade_date", pa.string()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("pre_close", pa.float64()),
        ("change", pa.float64()),
        ("pct_chg", pa.float64()),
        ("vol", pa.float64()),
        ("amount", pa.float64()),
        ("adj_factor", pa.float64()),
        ("up_limit", pa.float64()),
        ("down_limit", pa.float64()),
    ]
)


class KlineDailyWarehouseTransform:
    def normalize_for_parquet(self, df: pd.DataFrame) -> pa.Table:
        if df.empty:
            return _ARROW_SCHEMA.empty_table()

        out = df.copy()
        out["ts_code"] = out["ts_code"].astype(str)
        out["trade_date"] = out["trade_date"].astype(str)
        out = out.sort_values(["trade_date", "ts_code"], kind="mergesort").reset_index(
            drop=True,
        )
        out = out[[f.name for f in _ARROW_SCHEMA]]
        return pa.Table.from_pandas(out, schema=_ARROW_SCHEMA, preserve_index=False)


__all__ = ["KlineDailyWarehouseTransform"]
