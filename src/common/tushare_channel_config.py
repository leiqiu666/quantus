"""Tushare 接口渠道路由配置（读取 config/tushare_api_channels.json）。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

Channel = Literal["official", "stocktoday"]

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PROJECT_ROOT / "config/tushare_api_channels.json"


@lru_cache
def _load_raw(path: str | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else _DEFAULT_CONFIG
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Tushare 渠道配置不存在: {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def get_tushare_channel_config(path: str | None = None) -> dict[str, Any]:
    return _load_raw(path)


def list_configured_apis(path: str | None = None) -> tuple[str, ...]:
    apis = get_tushare_channel_config(path).get("apis") or {}
    return tuple(apis.keys())


def get_api_entry(api_name: str, path: str | None = None) -> dict[str, Any] | None:
    apis = get_tushare_channel_config(path).get("apis") or {}
    return apis.get((api_name or "").strip())


def resolve_channel(api_name: str, *, default: Channel = "official", path: str | None = None) -> Channel:
    """返回接口应使用的渠道；未配置时走 default。"""
    entry = get_api_entry(api_name, path)
    if not entry:
        return default
    ch = (entry.get("channel") or default).strip().lower()
    if ch not in ("official", "stocktoday"):
        return default
    return ch  # type: ignore[return-value]


def get_rate_limit(
    api_name: str,
    *,
    channel: Channel | None = None,
    path: str | None = None,
) -> int:
    """返回指定接口在对应渠道下的每分钟频次上限。"""
    entry = get_api_entry(api_name, path) or {}
    ch = channel or resolve_channel(api_name, path=path)
    limits = entry.get("rate_limit") or {}
    if ch == "stocktoday":
        meta = get_tushare_channel_config(path).get("_meta") or {}
        return int(limits.get("stocktoday") or meta.get("stocktoday_rate_limit_per_minute") or 100)
    return int(limits.get("official") or 200)
