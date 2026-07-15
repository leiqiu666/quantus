"""因子元数据查询 Service（API 只读路径）。"""

from __future__ import annotations

from typing import Optional

from src.model.kline.factor_meta_model import FactorMetaModel


def _impl_kind(r) -> str:
    kind = getattr(r, "impl_kind", None)
    if kind:
        return str(kind)
    src = (r.source or "").strip()
    if src == "国泰191":
        return "formula"
    if src == "自研":
        return "python"
    return "tushare"


class FactorMetaQueryService:
    def __init__(self) -> None:
        self._model = FactorMetaModel()

    def list_factors(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        source: Optional[str] = None,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> dict:
        page = max(1, page)
        page_size = min(max(1, page_size), 500)
        offset = (page - 1) * page_size
        rows, total = self._model.search(
            source=source,
            category=category,
            keyword=keyword,
            offset=offset,
            limit=page_size,
        )
        return {
            "items": [
                {
                    "factor_name": r.factor_name,
                    "display_name": r.display_name,
                    "source": r.source,
                    "category": r.category,
                    "formula": r.formula,
                    "impl_kind": _impl_kind(r),
                    "python_path": getattr(r, "python_path", None),
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "month_count": r.month_count,
                }
                for r in rows
            ],
            "total": total,
        }
