"""warehouse · 日 K Parquet Load：分区路径约定 + 整月覆盖写。"""

from __future__ import annotations

import uuid
from pathlib import Path

import pyarrow as pa

from src.common.setting import settings
from src.etl.load.warehouse.warehouse_parquet_load import ParquetLoad

_DATASET = "kline_daily"


class KlineDailyParquetLoad:
    def __init__(self) -> None:
        self._loader = ParquetLoad()
        self._root = Path(settings.warehouse_root)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def dataset_root(self) -> Path:
        return self._root / _DATASET

    def partition_dir(self, year_month: str) -> Path:
        return self.dataset_root / f"dt={year_month}"

    def write_month_partition(self, table: pa.Table, year_month: str) -> int:
        partition_rel = f"{_DATASET}/dt={year_month}"
        self._loader.remove_partition(self._root, partition_rel)
        file_path = self.partition_dir(year_month) / f"part-{uuid.uuid4().hex}.parquet"
        return self._loader.write_table(table, file_path)

    def list_existing_months(self) -> list[str]:
        if not self.dataset_root.exists():
            return []
        months: list[str] = []
        for entry in self.dataset_root.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if not name.startswith("dt="):
                continue
            ym = name[len("dt=") :]
            if len(ym) == 6 and ym.isdigit():
                months.append(ym)
        months.sort()
        return months


__all__ = ["KlineDailyParquetLoad"]
