"""warehouse · 日 K 单月 Workflow：PG → Arrow → Parquet 分区覆盖。"""

from __future__ import annotations

from src.etl.extract.warehouse.warehouse_kline_daily_pg_extract import KlineDailyPgExtract
from src.etl.load.warehouse.warehouse_kline_daily_parquet_load import KlineDailyParquetLoad
from src.etl.transform.warehouse.warehouse_kline_daily_transform import (
    KlineDailyWarehouseTransform,
)


class KlineDailyWarehouseWorkflow:
    def __init__(self) -> None:
        self._extract = KlineDailyPgExtract()
        self._transform = KlineDailyWarehouseTransform()
        self._load = KlineDailyParquetLoad()

    def dump_month(self, year_month: str) -> int:
        df = self._extract.read_month(year_month)
        if df.empty:
            return 0
        table = self._transform.normalize_for_parquet(df)
        return self._load.write_month_partition(table, year_month)


__all__ = ["KlineDailyWarehouseWorkflow"]
