"""warehouse · 日 K Parquet Extract：DuckDB 读 parquet 仓库，专供 check 路径用。

不与 `KlineDailyParquetLoad` 耦合 —— Load 只关心写、本类只关心读，分层清晰。
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.common.setting import settings

_DATASET = "kline_daily"


class KlineDailyParquetExtract:
    def __init__(self) -> None:
        self._root = Path(settings.warehouse_root)

    @property
    def dataset_root(self) -> Path:
        return self._root / _DATASET

    def _glob(self) -> str:
        return str(self.dataset_root / "**" / "*.parquet")

    def _empty(self) -> bool:
        if not self.dataset_root.exists():
            return True
        # 任意一个 dt=YYYYMM 子目录存在即非空（避免空仓库时 DuckDB 报 No files found）
        for entry in self.dataset_root.iterdir():
            if entry.is_dir() and entry.name.startswith("dt="):
                for f in entry.iterdir():
                    if f.suffix == ".parquet":
                        return False
        return True

    def count_by_month(self) -> dict[str, int]:
        """{YYYYMM: 行数}，dt 来自 Hive 目录名。空仓库返回 {}。"""
        if self._empty():
            return {}
        con = duckdb.connect()
        try:
            rows = con.execute(
                f"""
                SELECT CAST(dt AS VARCHAR) AS ym, COUNT(*) AS n
                FROM read_parquet('{self._glob()}', hive_partitioning=1)
                GROUP BY 1
                """
            ).fetchall()
        finally:
            con.close()
        out: dict[str, int] = {}
        for ym, n in rows:
            s = str(ym).strip()
            # DuckDB 把 dt 推断为 BIGINT；早期月如 "199012" 转回字符串保持 6 位
            if s.isdigit() and len(s) < 6:
                s = s.zfill(6)
            out[s] = int(n)
        return out

    def total_rows(self) -> int:
        if self._empty():
            return 0
        con = duckdb.connect()
        try:
            n = con.execute(
                f"SELECT COUNT(*) FROM read_parquet('{self._glob()}')"
            ).fetchone()[0]
        finally:
            con.close()
        return int(n)


__all__ = ["KlineDailyParquetExtract"]
