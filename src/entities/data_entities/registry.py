"""自动发现 data_entities 包下的 SQLAlchemy 实体类。"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Type

# 不参与扫描的模块名（basename）
_EXCLUDED_MODULES = frozenset({"cli", "registry", "user", "__init__"})


def _is_entity_class(cls: type) -> bool:
    tablename = getattr(cls, "__tablename__", None)
    if not tablename or not isinstance(tablename, str):
        return False
    return hasattr(cls, "__table__")


def discover_all_entities() -> list[Type]:
    """扫描 data_entities 目录，返回所有 ORM 实体类（按表名排序）。"""
    package_name = __package__
    package = importlib.import_module(package_name)
    entities: list[Type] = []

    prefix = package_name + "."
    for _importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix):
        if ispkg:
            continue
        short_name = modname.rsplit(".", 1)[-1]
        if short_name in _EXCLUDED_MODULES:
            continue

        module = importlib.import_module(modname)
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != modname:
                continue
            if _is_entity_class(obj):
                entities.append(obj)

    entities.sort(key=lambda cls: cls.__tablename__)
    return entities


ALL_ENTITIES: list[Type] = discover_all_entities()
