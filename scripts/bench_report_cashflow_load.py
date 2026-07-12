#!/usr/bin/env python3
"""对比 report_cashflow 一期：load_report(upsert) vs load_report_filter。"""

from __future__ import annotations

import statistics
import time

from src.entities.data_entities.report_cashflow_entities import ReportCashflowEntities
from src.etl.extract.local.financial.report_extract import ReportExtract as LocalReportExtract
from src.etl.load.financial.report_load import ReportLoad
from src.etl.transform.financial.report_transform import ReportTransform
from src.etl.workflow.financial.report_workflow import ReportWorkflow

PERIOD = "20260331"
ROUNDS = 3


def prepare_df():
    wf = ReportWorkflow()
    raw = wf.report_extract.pull_report_cashflow(period=PERIOD)
    raw = wf.report_transform.filter_report_by_delist(
        PERIOD, raw, stock_extract=wf.local_stock_extract
    )
    cleaned = wf.report_transform.report_transform_merge_now(raw)
    return wf.report_transform.report_more_detail_to_json(ReportCashflowEntities, cleaned)


def time_load(fn, rounds: int = ROUNDS) -> list[float]:
    samples: list[float] = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return samples


def summarize(name: str, samples: list[float], extra: str = "") -> None:
    med = statistics.median(samples)
    print(
        f"  {name}: min={min(samples):.3f}s med={med:.3f}s max={max(samples):.3f}s "
        f"avg={statistics.mean(samples):.3f}s {extra}"
    )


def main() -> None:
    print(f"=== report_cashflow Load 对比 period={PERIOD} rounds={ROUNDS} ===\n")

    print("[1] Extract + Transform（不计入 Load 对比）...")
    t0 = time.perf_counter()
    df = prepare_df()
    et_seconds = time.perf_counter() - t0
    row_count = len(df)
    print(f"    行数={row_count} 耗时={et_seconds:.3f}s\n")
    if row_count == 0:
        print("无数据，退出")
        return

    load = ReportLoad()
    local_extract = LocalReportExtract()
    existing = local_extract.get_report_rows_by_end_date("cashflow", PERIOD)
    print(f"[2] 库内已有 end_date={PERIOD} 行数: {len(existing)}\n")

    print(f"[3] Load 压测（同一 DataFrame，各跑 {ROUNDS} 轮）\n")

    upsert_samples = time_load(
        lambda: load.load_report(entities=ReportCashflowEntities, df=df),
        ROUNDS,
    )
    summarize("load_report (bulk_upsert)", upsert_samples)

    filter_samples: list[float] = []
    last_stats = ""
    for _ in range(ROUNDS):
        t0 = time.perf_counter()
        r = load.load_report_filter(
            entities=ReportCashflowEntities,
            df=df,
            scope_end_date=PERIOD,
            local_report_extract=local_extract,
        )
        filter_samples.append(time.perf_counter() - t0)
        last_stats = f"ins={r.inserted} upd={r.updated} skip={r.skipped}"
    summarize("load_report_filter", filter_samples, f"末轮 {last_stats}")

    upsert_med = statistics.median(upsert_samples)
    filter_med = statistics.median(filter_samples)
    if filter_med > 0:
        speedup = upsert_med / filter_med
        saved_pct = (1 - filter_med / upsert_med) * 100 if upsert_med > 0 else 0
        print(
            f"\n[4] 结论（中位数）: filter 相对 upsert "
            f"{'快' if speedup > 1 else '慢'} {abs(speedup - 1) * 100:.1f}% "
            f"（{upsert_med:.3f}s → {filter_med:.3f}s，约节省 {saved_pct:.1f}% 时间）"
        )

    print("\n[5] filter 查库分项（单轮，LocalExtract 链路）...")
    t_q = time.perf_counter()
    rows = local_extract.get_report_rows_by_end_date("cashflow", PERIOD)
    query_s = time.perf_counter() - t_q

    t_w = time.perf_counter()
    load.load_report_filter(
        ReportCashflowEntities,
        df,
        scope_end_date=PERIOD,
        local_report_extract=local_extract,
    )
    total_filter = time.perf_counter() - t_w
    print(f"  LocalExtract 查库: {query_s:.3f}s ({len(rows)} 行)")
    print(f"  完整 load_report_filter: {total_filter:.3f}s")


if __name__ == "__main__":
    main()
