"""因子元数据服务：扫描 Parquet + 注册表 → upsert PG factor_meta。"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import polars as pl

from src.common.database import Database
from src.common.setting import settings
from src.entities.data_entities.kline.factor_meta_entities import FactorMetaEntities
from src.research.factor.registry import FactorRegistry
from src.entities.client_entities.tushare_entities import (
    STK_FACTOR_PRO_FIELDS,
    STK_FACTOR_PRO_RENAME,
)


def _load_tushare_descriptions() -> dict[str, tuple[str, str]]:
    """从 docs/tushare因子.csv 读取 tushare原名 → (短名, 完整描述)。"""
    csv_path = Path(__file__).resolve().parents[3] / "docs" / "tushare因子.csv"
    if not csv_path.exists():
        return {}
    result: dict[str, tuple[str, str]] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 4:
                name = row[0].strip()
                raw_desc = row[3].strip()
                short = raw_desc.split("-")[0].strip() if "-" in raw_desc else raw_desc
                result[name] = (short, raw_desc)
    return result


def _tushare_factor_category(orig_name: str) -> str:
    """按 tushare 原始字段名推断分类。"""
    fundamentals = {
        "turnover_rate", "turnover_rate_f", "volume_ratio",
        "pe", "pe_ttm", "pb", "ps", "ps_ttm",
        "dv_ratio", "dv_ttm",
        "total_share", "float_share", "free_share", "total_mv", "circ_mv",
    }
    stats = {"downdays", "updays", "lowdays", "topdays"}
    if orig_name in fundamentals:
        return "基本面"
    if orig_name in stats:
        return "统计"
    return "技术"


class FactorMetaService:
    def __init__(self) -> None:
        self._db = Database()
        self._factor_root = Path(settings.warehouse_root) / "factor"

    def _scan_parquet_dates(self, factor_name: str) -> tuple[str | None, str | None, int]:
        """扫描某因子的 Parquet，返回 (start_date, end_date, month_count)。"""
        fdir = self._factor_root / factor_name
        if not fdir.exists():
            return None, None, 0

        months = []
        for d in fdir.iterdir():
            if d.is_dir() and d.name.startswith("dt="):
                ym = d.name[3:]
                if re.fullmatch(r"\d{6}", ym):
                    months.append(ym)

        if not months:
            return None, None, 0

        glob = str(fdir / "**" / "*.parquet")
        try:
            dates = (
                pl.scan_parquet(glob)
                .select("trade_date")
                .unique()
                .collect()
                .to_series()
                .sort()
                .to_list()
            )
            if dates:
                return dates[0], dates[-1], len(months)
        except Exception:
            pass

        months.sort()
        return months[0] + "01", months[-1] + "31", len(months)

    def update_meta(self) -> int:
        """扫描所有因子来源，upsert 到 PG factor_meta。"""
        self._db.ensure_table(FactorMetaEntities)

        records: list[dict] = []

        # 1. 自研因子（formula 含 adj_convention=hfq）
        FactorRegistry.auto_discover()
        for meta in FactorRegistry.list_all():
            start, end, mc = self._scan_parquet_dates(meta.name)
            params = dict(meta.params) if meta.params else {}
            params.setdefault("adj_convention", "hfq")
            records.append({
                "factor_name": meta.name,
                "display_name": meta.display_name,
                "source": "自研",
                "category": meta.category,
                "formula": str(params),
                "start_date": start,
                "end_date": end,
                "month_count": mc,
            })

        # 2. Tushare 因子
        tushare_descs = _load_tushare_descriptions()
        self_names = {m.name for m in FactorRegistry.list_all()}

        for orig in STK_FACTOR_PRO_FIELDS:
            if orig in ("ts_code", "trade_date"):
                continue
            local = STK_FACTOR_PRO_RENAME.get(orig, orig)
            if local in self_names:
                continue

            start, end, mc = self._scan_parquet_dates(local)
            short, full_desc = tushare_descs.get(orig, (local, orig))
            # formula 去掉与 display_name 重复的中文前缀，只保留参数部分
            params_part = full_desc.split("-", 1)[1] if "-" in full_desc else full_desc
            records.append({
                "factor_name": local,
                "display_name": short,
                "source": "tushare",
                "category": _tushare_factor_category(orig),
                "formula": f"{orig}｜{params_part}",
                "start_date": start,
                "end_date": end,
                "month_count": mc,
            })

        # 3. 国泰 191
        try:
            from src.research.factor.gtja.catalog import load_catalog

            reserved = {r["factor_name"] for r in records}
            for spec in load_catalog().values():
                if spec.name in reserved:
                    continue
                start, end, mc = self._scan_parquet_dates(spec.name)
                formula = spec.formula_raw
                if spec.skip_reason:
                    formula = f"{formula}｜[{spec.skip_reason}]" if formula else spec.skip_reason
                records.append({
                    "factor_name": spec.name,
                    "display_name": f"国泰Alpha{spec.n}",
                    "source": "国泰191",
                    "category": "gtja191",
                    "formula": formula,
                    "start_date": start,
                    "end_date": end,
                    "month_count": mc,
                })
        except Exception as e:
            print(f"  [警告] 国泰191 meta 跳过: {e}")

        if not records:
            print("无因子元数据需要更新")
            return 0

        saved = self._db.bulk_upsert_postgresql(
            model_class=FactorMetaEntities,
            records=records,
            conflict_keys=["factor_name"],
            skip_length_check=True,
        )

        by_source = {}
        for r in records:
            by_source.setdefault(r["source"], []).append(r)

        print(f"因子元数据：更新 {saved} 条")
        for src, items in sorted(by_source.items()):
            has_data = sum(1 for i in items if i["start_date"])
            print(f"  {src}: {len(items)} 个因子，{has_data} 个有 Parquet 数据")

        return saved
