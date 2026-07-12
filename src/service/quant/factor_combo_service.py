"""因子组合 CRUD Service。"""

from __future__ import annotations

from typing import Any

from src.model.kline.factor_combo_model import FactorComboModel


def _validate_items(items: list[dict] | None) -> list[dict]:
    if not items or len(items) < 2:
        raise ValueError("组合至少包含 2 个因子")
    out: list[dict] = []
    seen: set[str] = set()
    for raw in items:
        fname = str((raw or {}).get("factor_name") or "").strip()
        if not fname:
            raise ValueError("factor_name 不能为空")
        if fname in seen:
            raise ValueError(f"重复因子: {fname}")
        seen.add(fname)
        try:
            weight = float((raw or {}).get("weight", 1.0))
        except (TypeError, ValueError) as e:
            raise ValueError(f"权重无效: {fname}") from e
        if weight <= 0 or weight != weight:  # NaN
            raise ValueError(f"权重须为正数: {fname}")
        out.append({"factor_name": fname, "weight": weight})
    return out


def _row_to_dict(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "items": row.items or [],
        "remark": row.remark,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds")
        if row.created_at
        else None,
        "updated_at": row.updated_at.isoformat(sep=" ", timespec="seconds")
        if row.updated_at
        else None,
    }


class FactorComboService:
    def __init__(self) -> None:
        self._model = FactorComboModel()

    def list_combos(self) -> list[dict]:
        return [_row_to_dict(r) for r in self._model.list_all()]

    def get_combo(self, combo_id: int) -> dict | None:
        row = self._model.get(combo_id)
        return _row_to_dict(row) if row else None

    def create_combo(self, data: dict) -> dict:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("名称不能为空")
        if self._model.get_by_name(name) is not None:
            raise ValueError(f"组合名已存在: {name}")
        items = _validate_items(data.get("items"))
        remark = data.get("remark")
        row = self._model.create(name, items, remark)
        return _row_to_dict(row)

    def update_combo(self, combo_id: int, data: dict) -> dict:
        row = self._model.get(combo_id)
        if row is None:
            raise ValueError(f"组合不存在: {combo_id}")
        name = data.get("name")
        if name is not None:
            name = str(name).strip()
            if not name:
                raise ValueError("名称不能为空")
            other = self._model.get_by_name(name)
            if other is not None and other.id != combo_id:
                raise ValueError(f"组合名已存在: {name}")
        items = data.get("items")
        validated = _validate_items(items) if items is not None else None
        remark = data["remark"] if "remark" in data else None
        updated = self._model.update(
            combo_id,
            name=name,
            items=validated,
            remark=remark if "remark" in data else None,
        )
        if updated is None:
            raise ValueError(f"组合不存在: {combo_id}")
        return _row_to_dict(updated)

    def delete_combo(self, combo_id: int) -> None:
        if not self._model.delete(combo_id):
            raise ValueError(f"组合不存在: {combo_id}")
