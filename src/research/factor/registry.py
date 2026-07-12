"""因子注册表：自动发现 + 手动注册 + 查询。"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import ClassVar

from src.research.factor.base import BaseFactor, FactorMeta


class FactorRegistry:
    _factors: ClassVar[dict[str, BaseFactor]] = {}
    _discovered: ClassVar[bool] = False

    @classmethod
    def register(cls, factor: BaseFactor) -> None:
        meta = factor.meta()
        if meta.name in cls._factors:
            existing = cls._factors[meta.name].meta()
            if existing.version >= meta.version:
                return
        cls._factors[meta.name] = factor

    @classmethod
    def get(cls, name: str) -> BaseFactor:
        if name not in cls._factors:
            raise KeyError(f"因子 '{name}' 未注册。已注册: {list(cls._factors.keys())}")
        return cls._factors[name]

    @classmethod
    def list_all(cls) -> list[FactorMeta]:
        return sorted([f.meta() for f in cls._factors.values()], key=lambda m: m.name)

    @classmethod
    def auto_discover(cls) -> None:
        if cls._discovered:
            return
        cls._discovered = True

        import src.research.factor as factor_pkg

        for _importer, modname, ispkg in pkgutil.walk_packages(
            factor_pkg.__path__, prefix=factor_pkg.__name__ + "."
        ):
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            for _attr_name, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    issubclass(obj, BaseFactor)
                    and obj is not BaseFactor
                    and not inspect.isabstract(obj)
                ):
                    try:
                        cls.register(obj())
                    except Exception:
                        pass
