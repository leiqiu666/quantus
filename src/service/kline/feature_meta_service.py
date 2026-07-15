"""特征目录 Service：种子、分页查询、覆盖刷新。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import polars as pl

from src.common.setting import settings
from src.model.kline.feature_meta_model import FeatureMetaModel
from src.research.dataset.kline import KlineDataset

# 国泰 panel 符号表（与 gtja/engine._eval_alpha 对齐）
_SEED_FEATURES: list[dict[str, Any]] = [
    {
        "feature_name": "OPEN",
        "display_name": "开盘价（后复权）",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "open",
        "transform": "open * fill_null(adj_factor, 1.0) → open_adj",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 10,
        "remark": "国泰 OPEN",
    },
    {
        "feature_name": "HIGH",
        "display_name": "最高价（后复权）",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "high",
        "transform": "high * fill_null(adj_factor, 1.0) → high_adj",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 20,
        "remark": "国泰 HIGH",
    },
    {
        "feature_name": "LOW",
        "display_name": "最低价（后复权）",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "low",
        "transform": "low * fill_null(adj_factor, 1.0) → low_adj",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 30,
        "remark": "国泰 LOW",
    },
    {
        "feature_name": "CLOSE",
        "display_name": "收盘价（后复权）",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "close",
        "transform": "close * fill_null(adj_factor, 1.0) → close_adj",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 40,
        "remark": "国泰 CLOSE",
    },
    {
        "feature_name": "VOLUME",
        "display_name": "成交量",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "vol",
        "transform": "vol",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 50,
        "remark": "国泰 VOLUME",
    },
    {
        "feature_name": "VOL",
        "display_name": "成交量（别名）",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "vol",
        "transform": "vol",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 55,
        "remark": "VOLUME 别名",
    },
    {
        "feature_name": "AMOUNT",
        "display_name": "成交额",
        "feature_kind": "source",
        "source_kind": "kline_daily",
        "source_path": "parquet:kline_daily",
        "source_column": "amount",
        "transform": "amount",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 60,
        "remark": "国泰 AMOUNT",
    },
    {
        "feature_name": "VWAP",
        "display_name": "成交量加权均价",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "amount * 10 / vol（vol>0）",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": "AMOUNT * 10 / VOLUME",
        "enabled": 1,
        "sort_order": 70,
        "remark": "panel 内派生",
    },
    {
        "feature_name": "RET",
        "display_name": "日收益率",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "close_adj / shift(close_adj,1) - 1",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": "CLOSE / DELAY(CLOSE,1) - 1",
        "enabled": 1,
        "sort_order": 80,
        "remark": "panel 内派生",
    },
    {
        "feature_name": "DTM",
        "display_name": "上行波动（国泰简化）",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "见 gtja/engine._load_panel",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 90,
        "remark": "国泰 DTM",
    },
    {
        "feature_name": "DBM",
        "display_name": "下行波动（国泰简化）",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "见 gtja/engine._load_panel",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 100,
        "remark": "国泰 DBM",
    },
    {
        "feature_name": "HD",
        "display_name": "高点差",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "见 gtja/engine._load_panel",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 110,
        "remark": "国泰 HD",
    },
    {
        "feature_name": "LD",
        "display_name": "低点差",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "见 gtja/engine._load_panel",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 120,
        "remark": "国泰 LD",
    },
    {
        "feature_name": "TR",
        "display_name": "真实波幅",
        "feature_kind": "derived",
        "source_kind": "derived",
        "source_path": "parquet:kline_daily",
        "source_column": None,
        "transform": "见 gtja/engine._load_panel",
        "frequency": "daily",
        "domain": "stock",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 130,
        "remark": "国泰 TR",
    },
    {
        "feature_name": "BANCHMARKINDEXOPEN",
        "display_name": "基准指数开盘价",
        "feature_kind": "source",
        "source_kind": "index_daily",
        "source_path": "parquet:index_daily",
        "source_column": "open",
        "transform": "index_daily.open（默认 000300.SH）",
        "frequency": "daily",
        "domain": "index",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 200,
        "remark": "国泰拼写 BANCHMARK",
    },
    {
        "feature_name": "BANCHMARKINDEXCLOSE",
        "display_name": "基准指数收盘价",
        "feature_kind": "source",
        "source_kind": "index_daily",
        "source_path": "parquet:index_daily",
        "source_column": "close",
        "transform": "index_daily.close（默认 000300.SH）",
        "frequency": "daily",
        "domain": "index",
        "dtype": "float64",
        "formula": None,
        "enabled": 1,
        "sort_order": 210,
        "remark": "国泰拼写 BANCHMARK",
    },
]


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "id": r.id,
        "feature_name": r.feature_name,
        "display_name": r.display_name,
        "feature_kind": r.feature_kind,
        "source_kind": r.source_kind,
        "source_path": r.source_path,
        "source_column": r.source_column,
        "transform": r.transform,
        "frequency": r.frequency,
        "domain": r.domain,
        "dtype": r.dtype,
        "formula": r.formula,
        "start_date": r.start_date,
        "end_date": r.end_date,
        "enabled": r.enabled,
        "sort_order": r.sort_order,
        "remark": r.remark,
    }


class FeatureMetaService:
    def __init__(self) -> None:
        self._model = FeatureMetaModel()

    def list_features(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        feature_kind: Optional[str] = None,
        source_kind: Optional[str] = None,
        enabled: Optional[int] = None,
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        offset = (page - 1) * page_size
        rows, total = self._model.search(
            keyword=keyword,
            feature_kind=feature_kind,
            source_kind=source_kind,
            enabled=enabled,
            offset=offset,
            limit=page_size,
        )
        return {"items": [_row_to_dict(r) for r in rows], "total": total}

    def seed_defaults(self) -> dict[str, int]:
        for item in _SEED_FEATURES:
            self._model.upsert_by_name(dict(item), keep_coverage=True)
        return {"upserted": len(_SEED_FEATURES)}

    def update_feature(self, feature_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {
            "display_name",
            "feature_kind",
            "source_kind",
            "source_path",
            "source_column",
            "transform",
            "frequency",
            "domain",
            "dtype",
            "formula",
            "enabled",
            "sort_order",
            "remark",
        }
        payload = {k: v for k, v in fields.items() if k in allowed}
        if "feature_kind" in payload and payload["feature_kind"] not in (
            "source",
            "derived",
        ):
            raise ValueError("feature_kind 须为 source 或 derived")
        row = self._model.update_by_id(feature_id, payload)
        return None if row is None else _row_to_dict(row)

    def create_feature(self, fields: dict[str, Any]) -> dict[str, Any]:
        name = (fields.get("feature_name") or "").strip()
        if not name:
            raise ValueError("feature_name 不能为空")
        kind = fields.get("feature_kind") or "source"
        if kind not in ("source", "derived"):
            raise ValueError("feature_kind 须为 source 或 derived")
        payload = {
            "feature_name": name,
            "display_name": fields.get("display_name"),
            "feature_kind": kind,
            "source_kind": fields.get("source_kind") or "kline_daily",
            "source_path": fields.get("source_path"),
            "source_column": fields.get("source_column"),
            "transform": fields.get("transform"),
            "frequency": fields.get("frequency") or "daily",
            "domain": fields.get("domain") or "stock",
            "dtype": fields.get("dtype") or "float64",
            "formula": fields.get("formula"),
            "enabled": int(fields.get("enabled", 1)),
            "sort_order": int(fields.get("sort_order") or 0),
            "remark": fields.get("remark"),
        }
        row = self._model.create(payload)
        return _row_to_dict(row)

    def refresh_coverage(self) -> dict[str, Any]:
        kline_start, kline_end = self._scan_kline_range()
        index_start, index_end = self._scan_index_range()

        updated = 0
        if kline_start and kline_end:
            updated += self._model.update_coverage_by_source_kind(
                ["kline_daily", "derived"], kline_start, kline_end
            )
        if index_start and index_end:
            updated += self._model.update_coverage_by_source_kind(
                ["index_daily"], index_start, index_end
            )
        return {
            "updated": updated,
            "kline_start": kline_start,
            "kline_end": kline_end,
            "index_start": index_start,
            "index_end": index_end,
        }

    @staticmethod
    def _scan_kline_range() -> tuple[str | None, str | None]:
        try:
            ds = KlineDataset()
            months = ds.list_available_months()
            if not months:
                return None, None
            # 只扫首尾月，避免全库 collect
            ends = [months[0], months[-1]] if len(months) > 1 else [months[0]]
            frames = []
            for ym in ends:
                frames.append(
                    ds.read_month(ym).select(pl.col("trade_date").cast(pl.Utf8)).collect()
                )
            df = pl.concat(frames) if len(frames) > 1 else frames[0]
            if df.is_empty():
                return None, None
            return str(df["trade_date"].min()), str(df["trade_date"].max())
        except Exception:
            return None, None

    @staticmethod
    def _scan_index_range() -> tuple[str | None, str | None]:
        root = Path(settings.warehouse_root) / "index_daily"
        if root.exists():
            try:
                df = (
                    pl.scan_parquet(str(root / "**" / "*.parquet"))
                    .select(pl.col("trade_date").cast(pl.Utf8))
                    .collect()
                )
                if not df.is_empty():
                    return str(df["trade_date"].min()), str(df["trade_date"].max())
            except Exception:
                pass
        try:
            from sqlalchemy import func

            from src.common.database import Database
            from src.entities.data_entities.index.index_daily_entities import (
                IndexDailyEntities,
            )

            session = Database().get_session()
            try:
                mn, mx = session.query(
                    func.min(IndexDailyEntities.trade_date),
                    func.max(IndexDailyEntities.trade_date),
                ).one()
                if mn and mx:
                    return str(mn), str(mx)
            finally:
                session.close()
        except Exception:
            return None, None
        return None, None
