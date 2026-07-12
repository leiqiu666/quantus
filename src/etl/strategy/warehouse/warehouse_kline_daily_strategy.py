"""warehouse · 日 K Strategy：月份区间编排 + 99% 完整性守门 + 当月强制重写。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.extract.warehouse.warehouse_kline_daily_parquet_extract import (
    KlineDailyParquetExtract,
)
from src.etl.extract.warehouse.warehouse_kline_daily_pg_extract import KlineDailyPgExtract
from src.etl.load.warehouse.warehouse_kline_daily_parquet_load import KlineDailyParquetLoad
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.warehouse.warehouse_kline_daily_workflow import (
    KlineDailyWarehouseWorkflow,
)


PER_DAY_THRESHOLD = 0.99


def _month_iter(start_ym: str, end_ym: str) -> list[str]:
    """[start_ym, end_ym] 闭区间月份序列（YYYYMM 升序）。"""
    if start_ym > end_ym:
        return []
    y, m = int(start_ym[:4]), int(start_ym[4:])
    ey, em = int(end_ym[:4]), int(end_ym[4:])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def _default_start_month() -> str:
    raw = settings.etl_start_date("kline_daily").strip()
    if len(raw) >= 6 and raw[:6].isdigit():
        return raw[:6]
    return "20050101"[:6]


def _current_month() -> str:
    return datetime.now().strftime("%Y%m")


class KlineDailyWarehouseStrategy:
    def __init__(self) -> None:
        self._extract = KlineDailyPgExtract()
        self._parquet_extract = KlineDailyParquetExtract()
        self._workflow = KlineDailyWarehouseWorkflow()
        self._load = KlineDailyParquetLoad()
        self._trade_cal_strategy = TradeCalStrategy()

    def dump_by_month_range(
        self,
        start_month: str | None = None,
        end_month: str | None = None,
    ) -> int:
        start = (start_month or _default_start_month()).strip()
        end = (end_month or _current_month()).strip()
        if len(start) != 6 or not start.isdigit():
            raise ValueError(f"invalid start_month: {start_month!r}")
        if len(end) != 6 or not end.isdigit():
            raise ValueError(f"invalid end_month: {end_month!r}")

        # 确保区间内交易日历已落库，否则 expected 缺日导致全月 skip
        self._trade_cal_strategy.ensure_trade_cal(
            start_date=f"{start}01", end_date=f"{end}31", exchange="SSE",
        )

        months = _month_iter(start, end)
        if not months:
            print(f"[warehouse] 空区间 {start}~{end}，无月份可处理")
            return 0

        today = datetime.now().strftime("%Y%m%d")
        current_month = today[:6]

        existing = set(self._load.list_existing_months())
        missing = [m for m in months if m not in existing]
        targets: list[str] = sorted(set(missing))
        # 当月强制重写（每日覆盖捕获新增 trade_date / T+1 回填）
        if start <= current_month <= end and current_month not in targets:
            targets.append(current_month)
            targets.sort()

        if not targets:
            print(f"[warehouse] {start}~{end} 全部月份已落分区，无需重写")
            return 0

        print(
            f"[warehouse] 区间 {start}~{end}，已落 {len(existing)} 月，"
            f"待处理 {len(targets)} 月（含当月强制重写）"
        )

        total_rows = 0
        dumped = 0
        skipped = 0
        pbar = tqdm_iter(targets, desc="导出日K到Parquet", unit="月")
        for ym in pbar:
            opens = self._extract.list_open_trade_dates_by_month(ym)
            if not opens:
                skipped += 1
                pbar.write(f"[skip] {ym}: 该月无 SSE 开市日")
                pbar.set_postfix(month=ym, rows=0, total=total_rows, dumped=dumped, skipped=skipped)
                continue

            is_current = ym == current_month
            # 当月只对"已过去"的开市日做门槛检查，今日及未来不参与
            check_opens = [d for d in opens if d < today] if is_current else opens

            if check_opens:
                expected = self._extract.compute_expected_by_dates(check_opens)
                counts = self._extract.count_by_date(ym)
                short = [
                    d for d in check_opens
                    if counts.get(d, 0) < PER_DAY_THRESHOLD * expected.get(d, 0)
                ]
            else:
                short = []

            if short:
                preview = ", ".join(
                    f"{d}({counts.get(d, 0)}/{expected.get(d, 0)})" for d in short[:5]
                )
                more = "" if len(short) <= 5 else f" …+{len(short) - 5}"
                if is_current:
                    pbar.write(f"[warn] {ym}（当月）未达 99% 的已过去日 {len(short)} 天 — {preview}{more}（仍写入分区）")
                else:
                    skipped += 1
                    pbar.write(f"[skip] {ym}: 未达 99% 的日期 {len(short)} 天 — {preview}{more}")
                    pbar.set_postfix(month=ym, rows=0, total=total_rows, dumped=dumped, skipped=skipped)
                    continue

            n = self._workflow.dump_month(ym)
            total_rows += n
            dumped += 1
            pbar.set_postfix(month=ym, rows=n, total=total_rows, dumped=dumped, skipped=skipped)

        print(
            f"[warehouse] 完成：dump {dumped} 月 / skip {skipped} 月 / 累计写入 {total_rows} 行"
        )
        return total_rows

    def check_parquet_vs_pg(self) -> dict[str, list]:
        """PG vs Parquet 月度行数对账。

        分桶：
        - ok            : pg_n == pq_n
        - diff          : 两边都有但行数不一致（drift；需 rm 分区后重 dump）
        - pg_only       : PG 有 Parquet 无（多数是 99% 守门预期跳过；用 expected_skip 标识）
        - pq_only       : Parquet 有 PG 无（脏数据，正常不该出现）
        - expected_skip : pg_only 的子集，对应 dump 99% 跳过的月份

        返回结构：{"ok": [ym], "diff": [(ym, pg_n, pq_n)], "pg_only": [ym],
                  "pq_only": [ym], "expected_skip": [ym]}
        """
        print("[warehouse-check] 聚合 PG kline_daily 月度行数…")
        pg_counts = self._extract.count_by_month_all()
        print("[warehouse-check] 聚合 Parquet 仓库月度行数…")
        pq_counts = self._parquet_extract.count_by_month()

        months = sorted(set(pg_counts) | set(pq_counts))
        ok: list[str] = []
        diff: list[tuple[str, int, int]] = []
        pg_only: list[str] = []
        pq_only: list[str] = []
        for ym in months:
            pg_n = pg_counts.get(ym, 0)
            pq_n = pq_counts.get(ym, 0)
            if pg_n == pq_n:
                ok.append(ym)
            elif pq_n == 0:
                pg_only.append(ym)
            elif pg_n == 0:
                pq_only.append(ym)
            else:
                diff.append((ym, pg_n, pq_n))

        expected_skip = self._classify_expected_skip(pg_only)
        unexpected_pg_only = [m for m in pg_only if m not in expected_skip]

        pg_total = sum(pg_counts.values())
        pq_total = sum(pq_counts.values())
        total_diff = pg_total - pq_total

        self._print_check_report(
            pg_total=pg_total, pq_total=pq_total, total_diff=total_diff,
            ok=ok, diff=diff,
            pg_only=pg_only, expected_skip=expected_skip,
            unexpected_pg_only=unexpected_pg_only,
            pq_only=pq_only,
        )

        return {
            "ok": ok,
            "diff": diff,
            "pg_only": pg_only,
            "pq_only": pq_only,
            "expected_skip": expected_skip,
        }

    def _classify_expected_skip(self, pg_only_months: list[str]) -> list[str]:
        """pg_only 中哪些是 dump 99% 守门预期跳过的（与 dump_by_month_range 同口径）。"""
        if not pg_only_months:
            return []
        out: list[str] = []
        for ym in pg_only_months:
            opens = self._extract.list_open_trade_dates_by_month(ym)
            if not opens:
                # 无开市日 → dump 也会 skip（如 199012 SSE 无开市日）→ 算预期
                out.append(ym)
                continue
            expected = self._extract.compute_expected_by_dates(opens)
            day_count = self._extract.count_by_date(ym)
            short = any(
                day_count.get(d, 0) < PER_DAY_THRESHOLD * expected.get(d, 0)
                for d in opens
            )
            if short:
                out.append(ym)
        return out

    def _print_check_report(
        self, *,
        pg_total: int, pq_total: int, total_diff: int,
        ok: list[str], diff: list[tuple[str, int, int]],
        pg_only: list[str], expected_skip: list[str],
        unexpected_pg_only: list[str], pq_only: list[str],
    ) -> None:
        print("")
        print("=" * 60)
        print("[warehouse-check] PG vs Parquet 对账报告")
        print("=" * 60)
        print(f"总行数  PG: {pg_total:>12,}   Parquet: {pq_total:>12,}   diff: {total_diff:+,}")
        print(
            f"月份桶  ok: {len(ok)}   diff: {len(diff)}   "
            f"pg-only: {len(pg_only)}（含预期跳过 {len(expected_skip)}）   "
            f"pq-only: {len(pq_only)}"
        )
        print("")

        if diff:
            print(f"[diff] {len(diff)} 月行数不一致（需 rm -rf 分区后重 dump）：")
            for ym, pg_n, pq_n in diff[:20]:
                print(f"  {ym}  pg={pg_n}  pq={pq_n}  delta={pg_n - pq_n:+}")
            if len(diff) > 20:
                print(f"  …+{len(diff) - 20} 月")
            print("")

        if unexpected_pg_only:
            print(f"[pg-only · 非预期] {len(unexpected_pg_only)} 月 PG 有 / Parquet 无（dump 漏拉，需跑 dump 命令）：")
            print("  " + ", ".join(unexpected_pg_only[:30]))
            if len(unexpected_pg_only) > 30:
                print(f"  …+{len(unexpected_pg_only) - 30} 月")
            print("")

        if expected_skip:
            print(f"[pg-only · 99% 守门预期跳过] {len(expected_skip)} 月：")
            print("  " + ", ".join(expected_skip[:30]))
            if len(expected_skip) > 30:
                print(f"  …+{len(expected_skip) - 30} 月")
            print("")

        if pq_only:
            print(f"[pq-only] {len(pq_only)} 月 Parquet 有 / PG 无（脏数据，请检查）：")
            print("  " + ", ".join(pq_only[:30]))
            if len(pq_only) > 30:
                print(f"  …+{len(pq_only) - 30} 月")
            print("")

        if not diff and not unexpected_pg_only and not pq_only:
            print("✅ 已落分区与 PG 完全一致（差异仅来自 99% 守门预期跳过的早期月）")
        print("=" * 60)


__all__ = ["KlineDailyWarehouseStrategy"]
