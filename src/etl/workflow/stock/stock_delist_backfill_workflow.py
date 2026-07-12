"""从 kline_daily 最后交易日回填 stock_list.delist_date（名称含 (退) / （退））。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, or_

from src.common.database import Database
from src.entities.data_entities.kline.kline_daily_entities import KlineDailyEntities
from src.entities.data_entities.stock.stock_list_entities import StockListEntities


def _name_has_delist_suffix(name: str | None, fullname: str | None) -> bool:
    text = f"{name or ''}{fullname or ''}"
    return "(退)" in text or "（退）" in text


class StockDelistBackfillWorkflow:
    def __init__(self) -> None:
        self.db = Database()

    def list_delist_suffix_stocks(self) -> list[dict]:
        session = self.db.get_session()
        try:
            rows = (
                session.query(StockListEntities)
                .filter(
                    or_(
                        StockListEntities.name.like("%(退)%"),
                        StockListEntities.name.like("%（退）%"),
                        StockListEntities.fullname.like("%(退)%"),
                        StockListEntities.fullname.like("%（退）%"),
                    )
                )
                .order_by(StockListEntities.ts_code.asc())
                .all()
            )
            return [
                {
                    "ts_code": r.ts_code,
                    "name": (r.name or r.fullname or "").strip(),
                    "delist_date_before": (r.delist_date or "").strip() or None,
                }
                for r in rows
            ]
        finally:
            session.close()

    def _last_kline_dates(self, ts_codes: list[str]) -> dict[str, str]:
        if not ts_codes:
            return {}
        session = self.db.get_session()
        try:
            rows = (
                session.query(
                    KlineDailyEntities.ts_code,
                    func.max(KlineDailyEntities.trade_date),
                )
                .filter(KlineDailyEntities.ts_code.in_(ts_codes))
                .group_by(KlineDailyEntities.ts_code)
                .all()
            )
            out: dict[str, str] = {}
            for ts_code, max_td in rows:
                if max_td:
                    out[str(ts_code).strip()] = str(max_td).strip()[:8]
            return out
        finally:
            session.close()

    def backfill_delist_date_from_kline(
        self,
        *,
        dry_run: bool = False,
        report_path: str | None = None,
    ) -> dict[str, int | str]:
        stocks = self.list_delist_suffix_stocks()
        codes = [s["ts_code"] for s in stocks if s["ts_code"]]
        last_kline = self._last_kline_dates(codes)

        updated = 0
        skipped_no_kline = 0
        skipped_unchanged = 0
        report_rows: list[dict[str, str | None]] = []

        session = self.db.get_session()
        try:
            for item in stocks:
                ts_code = item["ts_code"]
                last_td = last_kline.get(ts_code or "")
                row = {
                    "name": item["name"],
                    "ts_code": ts_code,
                    "last_kline": last_td or None,
                    "delist_date_before": item["delist_date_before"],
                    "delist_date_after": last_td if last_td else None,
                    "updated": "否",
                }
                if not last_td:
                    skipped_no_kline += 1
                    report_rows.append(row)
                    continue
                if item["delist_date_before"] == last_td:
                    skipped_unchanged += 1
                    row["updated"] = "已是"
                    report_rows.append(row)
                    continue
                if not dry_run:
                    entity = (
                        session.query(StockListEntities)
                        .filter(StockListEntities.ts_code == ts_code)
                        .first()
                    )
                    if entity is not None:
                        entity.delist_date = last_td
                        updated += 1
                        row["updated"] = "是"
                else:
                    updated += 1
                    row["updated"] = "待写"
                report_rows.append(row)
            if not dry_run:
                session.commit()
        finally:
            session.close()

        if report_path:
            self._write_report(report_path, report_rows)

        return {
            "total": len(stocks),
            "updated": updated,
            "skipped_no_kline": skipped_no_kline,
            "skipped_unchanged": skipped_unchanged,
            "report_path": report_path or "",
        }

    def _write_report(self, path: str, rows: list[dict[str, str | None]]) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 名称含 (退) / （退）股票 delist_date 回填",
            "",
            f"> 共 **{len(rows)}** 只；`delist_date` = `kline_daily` 最后 `trade_date`。",
            "",
            "| 股票名称 | 股票代码 | 最后日K | 原 delist_date | 新 delist_date | 已更新 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for r in rows:
            name = (r["name"] or "—").replace("|", "\\|")
            lines.append(
                f"| {name} | {r['ts_code']} | {r['last_kline'] or '—'} | "
                f"{r['delist_date_before'] or '—'} | {r['delist_date_after'] or '—'} | {r['updated']} |"
            )
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
