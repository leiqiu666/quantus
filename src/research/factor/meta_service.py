"""因子元数据服务：扫描 Parquet + 注册表 → upsert PG factor_meta。"""

from __future__ import annotations

import csv
import inspect
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

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PYTHON_FACTOR_PREFIX = "src.research.factor.python."


def _load_tushare_descriptions() -> dict[str, tuple[str, str]]:
    """从 docs/tushare因子.csv 读取 tushare原名 → (短名, 完整描述)。"""
    csv_path = _REPO_ROOT / "docs" / "tushare因子.csv"
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


def _python_path_for_factor(factor) -> str | None:
    try:
        mod = factor.__class__.__module__ or ""
        if not mod.startswith(_PYTHON_FACTOR_PREFIX):
            return None
        path = Path(inspect.getfile(factor.__class__)).resolve()
        return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
    except Exception:
        return None


class FactorMetaService:
    def __init__(self) -> None:
        self._db = Database()
        self._factor_root = Path(settings.warehouse_root) / "factor"

    def _scan_parquet_dates(self, factor_name: str) -> tuple[str | None, str | None, int]:
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

    def _existing_formulas(self) -> dict[str, str]:
        from src.model.kline.factor_meta_model import FactorMetaModel

        try:
            return FactorMetaModel().list_formula_map()
        except Exception:
            return {}

    def update_meta(self) -> int:
        self._db.ensure_table(FactorMetaEntities)
        existing_formulas = self._existing_formulas()

        records: list[dict] = []

        FactorRegistry.auto_discover()
        for meta in FactorRegistry.list_all():
            start, end, mc = self._scan_parquet_dates(meta.name)
            params = dict(meta.params) if meta.params else {}
            params.setdefault("adj_convention", "hfq")
            factor = FactorRegistry.get(meta.name)
            py_path = _python_path_for_factor(factor)
            records.append({
                "factor_name": meta.name,
                "display_name": meta.display_name,
                "source": "自研",
                "category": meta.category,
                "formula": str(params),
                "impl_kind": "python",
                "python_path": py_path,
                "start_date": start,
                "end_date": end,
                "month_count": mc,
            })

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
            params_part = full_desc.split("-", 1)[1] if "-" in full_desc else full_desc
            records.append({
                "factor_name": local,
                "display_name": short,
                "source": "tushare",
                "category": _tushare_factor_category(orig),
                "formula": f"{orig}｜{params_part}",
                "impl_kind": "tushare",
                "python_path": None,
                "start_date": start,
                "end_date": end,
                "month_count": mc,
            })

        try:
            from src.research.factor.gtja.catalog import load_catalog

            reserved = {r["factor_name"] for r in records}
            for spec in load_catalog().values():
                if spec.name in reserved:
                    continue
                start, end, mc = self._scan_parquet_dates(spec.name)
                catalog_formula = spec.formula_raw
                if spec.skip_reason:
                    catalog_formula = (
                        f"{catalog_formula}｜[{spec.skip_reason}]"
                        if catalog_formula
                        else spec.skip_reason
                    )
                # 后台编辑过的公式优先保留（跳过原因后缀的 catalog 种子不覆盖用户公式）
                preserved = existing_formulas.get(spec.name)
                if preserved and "｜[" not in (preserved or ""):
                    formula = preserved
                elif preserved and not catalog_formula:
                    formula = preserved
                else:
                    # 若保留的是带 skip 的旧值且 catalog 有正文，仍允许用 preserved
                    formula = preserved if preserved else catalog_formula
                records.append({
                    "factor_name": spec.name,
                    "display_name": f"国泰Alpha{spec.n}",
                    "source": "国泰191",
                    "category": "gtja191",
                    "formula": formula,
                    "impl_kind": "formula",
                    "python_path": None,
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

        by_source: dict[str, list] = {}
        for r in records:
            by_source.setdefault(r["source"], []).append(r)

        print(f"因子元数据：更新 {saved} 条")
        for src, items in sorted(by_source.items()):
            has_data = sum(1 for i in items if i["start_date"])
            print(f"  {src}: {len(items)} 个因子，{has_data} 个有 Parquet 数据")

        return saved
