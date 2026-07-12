"""通达信 tq 通用 HTTP 代理服务。"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from src.common.setting import settings
from src.common.tdx_codec import serialize_tq_result
from src.common.tdx_local import TdxLocalClient

logger = logging.getLogger(__name__)

# 生命周期与需 callback 的接口不可通过 HTTP 代理
_BLOCKED_FUNCTIONS = frozenset(
    {
        "initialize",
        "close",
        "subscribe_hq",
        "subscribe_quote",
        "unsubscribe_hq",
        "_auto_initialize",
        "_auto_close",
        "_release",
        "_reInitialize",
    }
)

_client: TdxLocalClient | None = None


def is_enabled() -> bool:
    """是否配置为启动本地通达信（见 .env TDX_QUANT_ENABLED）。"""
    return settings.tdx_quant_enabled


def is_ready() -> bool:
    """本地通达信客户端是否已成功初始化。"""
    return _client is not None


def startup() -> None:
    """API 启动时初始化通达信连接。"""
    global _client
    if not is_enabled():
        logger.info("TDX_QUANT_ENABLED=false，跳过通达信本地客户端初始化")
        return
    _client = TdxLocalClient()
    _client._ensure_tq()
    logger.info("通达信本地客户端已初始化（TDX_ROOT=%s）", settings.tdx_root)


def shutdown() -> None:
    """API 关闭时释放通达信连接。"""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _get_client() -> TdxLocalClient:
    if not is_enabled():
        raise RuntimeError(
            "通达信本地服务未启用，请在 .env 设置 TDX_QUANT_ENABLED=true 并配置 TDX_ROOT（仅 Windows）"
        )
    if _client is None:
        raise RuntimeError("通达信服务未初始化，请确认 API 已正常启动且 TDX 路径有效")
    return _client


def list_functions() -> list[str]:
    """返回可通过 HTTP 调用的 tq 公开函数名。"""
    client = _get_client()
    names: list[str] = []
    for name, member in inspect.getmembers(client.tq, predicate=callable):
        if name.startswith("_"):
            continue
        if name in _BLOCKED_FUNCTIONS:
            continue
        names.append(name)
    return sorted(names)


def invoke(function_name: str, params: dict[str, Any] | None = None) -> Any:
    """按函数名反射调用 tq 并序列化返回值。"""
    if function_name.startswith("_") or function_name in _BLOCKED_FUNCTIONS:
        raise ValueError(f"函数 {function_name!r} 不允许通过 HTTP 调用")

    client = _get_client()
    fn = getattr(client.tq, function_name, None)
    if fn is None or not callable(fn):
        raise ValueError(f"未知 tq 函数: {function_name!r}")

    result = fn(**(params or {}))
    return serialize_tq_result(result)
