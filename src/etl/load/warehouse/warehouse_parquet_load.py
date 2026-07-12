"""warehouse · 通用 Parquet Load：分区目录清理 + 单文件写入。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


class ParquetLoad:
    def remove_partition(self, root: Path, partition_path: str) -> None:
        target = Path(root) / partition_path
        if target.exists():
            shutil.rmtree(target)

    def write_table(
        self,
        table: pa.Table,
        file_path: Path,
        *,
        compression: str = "zstd",
        compression_level: int = 3,
        row_group_size: int = 128_000,
        use_dictionary: bool = True,
    ) -> int:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(
            table,
            file_path,
            compression=compression,
            compression_level=compression_level,
            row_group_size=row_group_size,
            use_dictionary=use_dictionary,
        )
        return table.num_rows


__all__ = ["ParquetLoad"]
