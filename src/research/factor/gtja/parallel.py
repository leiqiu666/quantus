"""国泰191 月内多进程并行：核数探测 + Alpha 分片。"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def resolve_parallelism(
    n_alphas: int,
    workers: int | None = None,
    *,
    reserve: int = 1,
) -> tuple[int, int]:
    """返回 (worker_进程数, 每进程 POLARS_MAX_THREADS)。"""
    logical = os.cpu_count() or 1
    n = max(int(n_alphas), 0)
    if n <= 0:
        return 1, max(1, logical)

    if workers is not None:
        w = int(workers)
    else:
        env = (os.environ.get("GTJA191_WORKERS") or "").strip()
        if env:
            w = int(env)
        else:
            w = logical - max(int(reserve), 0)

    w = max(1, min(w, n, logical))
    polars_threads = max(1, logical // w)
    return w, polars_threads


def shard_alpha_ids(alpha_ids: list[int], n_shards: int) -> list[list[int]]:
    if n_shards <= 1 or len(alpha_ids) <= 1:
        return [list(alpha_ids)]
    n_shards = min(n_shards, len(alpha_ids))
    shards: list[list[int]] = [[] for _ in range(n_shards)]
    for i, aid in enumerate(alpha_ids):
        shards[i % n_shards].append(aid)
    return [s for s in shards if s]


def _worker_compute_shard(payload: dict[str, Any]) -> dict[str, Any]:
    """子进程入口：读临时面板，计算分配到的 Alpha，写 Parquet。"""
    os.environ["POLARS_MAX_THREADS"] = str(int(payload["polars_threads"]))

    import polars as pl

    from src.research.factor.gtja.catalog import load_catalog
    from src.research.factor.gtja.engine import Gtja191Engine

    panel_path = payload["panel_path"]
    year_month = payload["year_month"]
    alpha_ids: list[int] = payload["alpha_ids"]
    warehouse_root = payload["warehouse_root"]

    panel = pl.read_parquet(panel_path)
    catalog = load_catalog()
    specs = [catalog[i] for i in alpha_ids if i in catalog and not catalog[i].skip_compute]
    eng = Gtja191Engine(warehouse_root=warehouse_root)
    results, failed = eng._eval_and_write_specs(panel, year_month, specs)
    return {"results": results, "failed": failed}


def run_alpha_shards(
    *,
    panel_path: str,
    year_month: str,
    alpha_ids: list[int],
    warehouse_root: str,
    workers: int,
    polars_threads: int,
) -> tuple[dict[str, int], list[str]]:
    """在进程池中分片计算；返回 (results, failed_names)。"""
    shards = shard_alpha_ids(alpha_ids, workers)
    if not shards:
        return {}, []
    if len(shards) == 1:
        out = _worker_compute_shard(
            {
                "panel_path": panel_path,
                "year_month": year_month,
                "alpha_ids": shards[0],
                "warehouse_root": warehouse_root,
                "polars_threads": polars_threads,
            }
        )
        return out["results"], out["failed"]

    results: dict[str, int] = {}
    failed: list[str] = []
    payloads = [
        {
            "panel_path": panel_path,
            "year_month": year_month,
            "alpha_ids": shard,
            "warehouse_root": warehouse_root,
            "polars_threads": polars_threads,
        }
        for shard in shards
    ]
    with ProcessPoolExecutor(max_workers=len(shards)) as pool:
        futs = [pool.submit(_worker_compute_shard, p) for p in payloads]
        for fut in as_completed(futs):
            part = fut.result()
            results.update(part["results"])
            failed.extend(part["failed"])
    return results, failed


def panel_temp_path(warehouse_root: Path, year_month: str) -> Path:
    tmp = warehouse_root / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp / f"gtja_panel_{year_month}_{os.getpid()}.parquet"
