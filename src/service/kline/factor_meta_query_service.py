"""因子元数据查询 Service（API 只读路径）。"""

from __future__ import annotations

from typing import Optional

from src.model.kline.factor_meta_model import FactorMetaModel


class FactorMetaQueryService:
    def __init__(self) -> None:
        self._model = FactorMetaModel()

    def list_factors(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        rows = self._model.search(source=source, category=category)
        return [
            {
                "factor_name": r.factor_name,
                "display_name": r.display_name,
                "source": r.source,
                "category": r.category,
                "formula": r.formula,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "month_count": r.month_count,
            }
            for r in rows
        ]
