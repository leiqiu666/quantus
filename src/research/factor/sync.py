"""因子 PG 热层同步：Parquet → PG factor_latest 宽表。

列集合 = 自研 FactorRegistry ∪（factor_meta 中 source=tushare 且 Parquet 目录存在）。
研究/回测权威源仍是 Parquet factor/{name}/；本模块仅服务近端热层展示。
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from sqlalchemy import inspect, text

from src.common.database import Database
from src.common.setting import settings
from src.entities.data_entities.kline.factor_latest_entities import FactorLatestEntities
from src.entities.data_entities.kline.factor_meta_entities import FactorMetaEntities
from src.research.factor.registry import FactorRegistry


class FactorSyncService:
    def __init__(self) -> None:
        self._db = Database()
        self._warehouse = Path(settings.warehouse_root)
        self._kline_dir = self._warehouse / "kline_daily"
        self._factor_dir = self._warehouse / "factor"

    def ensure_table(self) -> None:
        self._db.ensure_table(FactorLatestEntities)

    def resolve_factor_names(self, source: str = "all") -> list[tuple[str, str]]:
        """
        返回 [(factor_name, display_or_comment), ...]。

        source: self | tushare | all
        """
        src = (source or "all").strip().lower()
        if src in ("self", "自研"):
            src = "self"
        elif src == "tushare":
            src = "tushare"
        else:
            src = "all"

        FactorRegistry.auto_discover()
        self_metas = {m.name: m.display_name for m in FactorRegistry.list_all()}
        result: list[tuple[str, str]] = []

        if src in ("self", "all"):
            for name, disp in sorted(self_metas.items()):
                if (self._factor_dir / name).exists():
                    result.append((name, disp))

        if src in ("tushare", "all"):
            sources = ("tushare",) if src == "tushare" else ("tushare", "国泰191")
            session = self._db.get_session()
            try:
                self._db.ensure_table(FactorMetaEntities)
                rows = (
                    session.query(
                        FactorMetaEntities.factor_name,
                        FactorMetaEntities.display_name,
                    )
                    .filter(FactorMetaEntities.source.in_(sources))
                    .all()
                )
            finally:
                session.close()

            self_names = set(self_metas)
            for fname, disp in rows:
                name = (fname or "").strip()
                if not name or name in self_names:
                    continue
                if not (self._factor_dir / name).exists():
                    continue
                result.append((name, (disp or name).strip() or name))

        # 去重保序
        seen: set[str] = set()
        uniq: list[tuple[str, str]] = []
        for name, disp in result:
            if name not in seen:
                seen.add(name)
                uniq.append((name, disp))
        return uniq

    def ensure_factor_columns(self, source: str = "all") -> list[str]:
        """检查 PG 列 vs 目标因子，缺列则 ALTER TABLE ADD COLUMN。"""
        insp = inspect(self._db.engine)
        existing = {c["name"] for c in insp.get_columns("factor_latest")}

        added = []
        for name, disp in self.resolve_factor_names(source):
            if name not in existing:
                safe_disp = disp.replace("'", "''")
                sql = f'ALTER TABLE "factor_latest" ADD COLUMN "{name}" FLOAT'
                with self._db.engine.begin() as conn:
                    conn.execute(text(sql))
                    comment_sql = (
                        f'COMMENT ON COLUMN "factor_latest"."{name}" '
                        f"IS '{safe_disp}'"
                    )
                    conn.execute(text(comment_sql))
                added.append(name)
                print(f"  [新列] factor_latest.{name} ({disp})")

        return added

    def _recent_trade_dates(self, days: int) -> list[str]:
        """从日 K Parquet 获取最近 N 个交易日。"""
        glob = str(self._kline_dir / "**" / "*.parquet")
        dates = (
            pl.scan_parquet(glob)
            .select("trade_date")
            .unique()
            .sort("trade_date", descending=True)
            .head(days)
            .collect()
            .to_series()
            .sort()
            .to_list()
        )
        return dates

    def _months_for_dates(self, dates: list[str]) -> list[str]:
        """从交易日列表推出需要读取的月份。"""
        return sorted({d[:6] for d in dates})

    def sync_to_pg(self, days: int = 60, source: str = "all") -> int:
        """从 Parquet 读最近 N 天因子值 → 合并宽表 → upsert PG。"""
        self.ensure_table()
        self.ensure_factor_columns(source=source)

        named = self.resolve_factor_names(source)
        factor_names = [n for n, _ in named]
        if not factor_names:
            print("无目标因子，跳过同步")
            return 0

        trade_dates = self._recent_trade_dates(days)
        if not trade_dates:
            print("无可用交易日，跳过同步")
            return 0

        months = self._months_for_dates(trade_dates)
        date_set = set(trade_dates)

        merged: pl.DataFrame | None = None

        for fname in factor_names:
            factor_dir = self._factor_dir / fname
            globs = []
            for ym in months:
                pdir = factor_dir / f"dt={ym}"
                if pdir.exists():
                    globs.append(str(pdir / "*.parquet"))

            if not globs:
                continue

            df = (
                pl.scan_parquet(globs)
                .filter(pl.col("trade_date").is_in(date_set))
                .select("ts_code", "trade_date", pl.col("value").alias(fname))
                .collect()
            )

            if df.is_empty():
                continue

            if merged is None:
                merged = df
            else:
                merged = merged.join(df, on=["ts_code", "trade_date"], how="full", coalesce=True)

        if merged is None or merged.is_empty():
            print("无因子数据可同步")
            return 0

        records = merged.to_dicts()
        for row in records:
            for k, v in row.items():
                if v is not None and v != v:
                    row[k] = None

        saved = self._raw_upsert(records, factor_names)

        deleted = self.cleanup_old(days, trade_dates)
        print(
            f"PG 同步完成：source={source}，upsert {saved} 行，"
            f"清理 {deleted} 行（保留最近 {days} 个交易日，{len(factor_names)} 列）"
        )
        return saved

    def _raw_upsert(self, records: list[dict], factor_names: list[str]) -> int:
        """原生 SQL upsert — 绕过 ORM 模型列过滤，支持动态因子列。"""
        if not records:
            return 0

        present = set(records[0].keys())
        all_cols = ["ts_code", "trade_date"] + [f for f in factor_names if f in present]
        if len(all_cols) <= 2:
            return 0

        placeholders = ", ".join(f":{c}" for c in all_cols)
        col_list = ", ".join(f'"{c}"' for c in all_cols)
        update_set = ", ".join(
            f'"{c}" = EXCLUDED."{c}"' for c in all_cols if c not in ("ts_code", "trade_date")
        )

        sql = (
            f'INSERT INTO "factor_latest" ({col_list}) VALUES ({placeholders}) '
            f"ON CONFLICT (ts_code, trade_date) DO UPDATE SET {update_set}"
        )

        session = self._db.get_session()
        try:
            chunk_size = 5000
            total = 0
            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]
                session.execute(text(sql), chunk)
                total += len(chunk)
            session.commit()
            return total
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def cleanup_old(self, days: int = 60, trade_dates: list[str] | None = None) -> int:
        """删除超过 N 个交易日的旧数据。"""
        if trade_dates is None:
            trade_dates = self._recent_trade_dates(days)
        if not trade_dates:
            return 0

        cutoff = min(trade_dates)
        session = self._db.get_session()
        try:
            result = session.execute(
                text("DELETE FROM factor_latest WHERE trade_date < :cutoff"),
                {"cutoff": cutoff},
            )
            session.commit()
            return result.rowcount or 0
        finally:
            session.close()
