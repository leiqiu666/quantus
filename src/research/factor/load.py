"""因子值 Parquet 写入 — 复用 ParquetLoad 基础设施。"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pyarrow as pa

from src.common.setting import settings
from src.etl.load.warehouse.warehouse_parquet_load import ParquetLoad


class FactorParquetLoad:
    def __init__(self, warehouse_root: str | None = None) -> None:
        self._loader = ParquetLoad()
        self._root = Path(warehouse_root or settings.warehouse_root)

    def factor_dir(self, factor_name: str) -> Path:
        return self._root / "factor" / factor_name

    def partition_dir(self, factor_name: str, year_month: str) -> Path:
        return self.factor_dir(factor_name) / f"dt={year_month}"

    def write_month_partition(
        self, table: pa.Table, factor_name: str, year_month: str
    ) -> int:
        partition_rel = f"factor/{factor_name}/dt={year_month}"
        self._loader.remove_partition(self._root, partition_rel)
        file_path = (
            self.partition_dir(factor_name, year_month)
            / f"part-{uuid.uuid4().hex}.parquet"
        )
        return self._loader.write_table(table, file_path)

    def list_existing_months(self, factor_name: str) -> list[str]:
        fdir = self.factor_dir(factor_name)
        if not fdir.exists():
            return []
        months = []
        for d in fdir.iterdir():
            if d.is_dir() and d.name.startswith("dt="):
                ym = d.name[3:]
                if re.fullmatch(r"\d{6}", ym):
                    months.append(ym)
        return sorted(months)
