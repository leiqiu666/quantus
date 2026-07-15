"""因子元数据管理 Service：详情 / 更新 / 源码只读。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.model.kline.factor_meta_model import FactorMetaModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PYTHON_DIR = (_REPO_ROOT / "src" / "research" / "factor" / "python").resolve()


def _row_to_dict(r) -> dict[str, Any]:
    return {
        "factor_name": r.factor_name,
        "display_name": r.display_name,
        "source": r.source,
        "category": r.category,
        "formula": r.formula,
        "impl_kind": getattr(r, "impl_kind", None) or _infer_impl_kind(r),
        "python_path": getattr(r, "python_path", None),
        "start_date": r.start_date,
        "end_date": r.end_date,
        "month_count": r.month_count,
    }


def _infer_impl_kind(r) -> str:
    src = (r.source or "").strip()
    if src == "国泰191":
        return "formula"
    if src == "自研":
        return "python"
    if src == "tushare":
        return "tushare"
    return "tushare"


class FactorMetaAdminService:
    def __init__(self) -> None:
        self._model = FactorMetaModel()

    def get_factor(self, factor_name: str) -> dict[str, Any] | None:
        row = self._model.get_by_name(factor_name)
        return None if row is None else _row_to_dict(row)

    def update_factor(self, factor_name: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = self._model.get_by_name(factor_name)
        if row is None:
            raise ValueError(f"因子不存在: {factor_name}")
        impl = getattr(row, "impl_kind", None) or _infer_impl_kind(row)
        allowed = {"display_name", "category"}
        if impl == "formula":
            allowed.add("formula")
        payload = {k: v for k, v in fields.items() if k in allowed}
        if "formula" in fields and impl != "formula":
            raise ValueError("仅 formula 类型因子可编辑公式")
        updated = self._model.update_by_name(factor_name, payload)
        if updated is None:
            raise ValueError(f"因子不存在: {factor_name}")
        return _row_to_dict(updated)

    def read_source(self, factor_name: str) -> dict[str, Any]:
        row = self._model.get_by_name(factor_name)
        if row is None:
            raise ValueError(f"因子不存在: {factor_name}")
        impl = getattr(row, "impl_kind", None) or _infer_impl_kind(row)
        if impl != "python":
            raise ValueError("仅 python 类型因子可读取源码")
        rel = (getattr(row, "python_path", None) or "").strip()
        if not rel:
            raise ValueError("未登记 python_path，请先运行 factor update-meta")
        path = (_REPO_ROOT / rel).resolve()
        try:
            path.relative_to(_PYTHON_DIR)
        except ValueError as e:
            raise ValueError(f"源码路径不在白名单目录: {rel}") from e
        if not path.is_file():
            raise FileNotFoundError(f"源码文件不存在: {rel}")
        return {
            "factor_name": factor_name,
            "python_path": rel,
            "content": path.read_text(encoding="utf-8"),
        }
