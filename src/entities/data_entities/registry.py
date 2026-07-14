"""自动发现 data_entities 包下的 SQLAlchemy 实体类。"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Type

# 不参与扫描的模块名（basename）
_EXCLUDED_MODULES = frozenset({"cli", "registry", "user", "__init__"})


def _is_entity_class(cls: type) -> bool:
    tablename = getattr(cls, "__tablename__", None)
    if not tablename or not isinstance(tablename, str):
        return False
    return hasattr(cls, "__table__")


def discover_all_entities() -> list[Type]:
    """递归扫描 data_entities（含 financial/market 等子目录），返回全部 ORM 实体。"""
    package_name = __package__
    package = importlib.import_module(package_name)
    root = Path(next(iter(package.__path__)))
    entities: list[Type] = []
    seen_tables: set[str] = set()

    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("_") or path.stem in _EXCLUDED_MODULES:
            continue
        rel = path.relative_to(root).with_suffix("")
        modname = package_name + "." + ".".join(rel.parts)
        module = importlib.import_module(modname)
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != modname:
                continue
            if not _is_entity_class(obj):
                continue
            table = obj.__tablename__
            if table in seen_tables:
                continue
            seen_tables.add(table)
            entities.append(obj)

    entities.sort(key=lambda cls: cls.__tablename__)
    return entities


ALL_ENTITIES: list[Type] = discover_all_entities()
