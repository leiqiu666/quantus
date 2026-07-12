"""通达信 TQ 本地客户端，仅供 API 进程在 Windows 上调用 tqcenter。"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.setting import settings

_STOCK_CODE_PATTERN = re.compile(r"^[0-9A-Za-z-]+\.[A-Z]{2,3}$")

_tq_module: Any | None = None
_tq_initialized = False


class TdxLocalClient:
    """封装 tqcenter.tq 的初始化与市场数据接口。"""

    def __init__(self) -> None:
        self._init_path = str(Path(__file__).resolve())

    def _ensure_tq(self) -> Any:
        global _tq_module, _tq_initialized

        if _tq_module is not None and _tq_initialized:
            return _tq_module

        user_dir = settings.tdx_pyplugins_user
        dll_path = settings.tdx_dll_path

        if not settings.tdx_root.strip():
            raise RuntimeError("TDX_ROOT 未配置，请在 .env 中设置通达信安装根目录")
        if not user_dir.is_dir():
            raise RuntimeError(f"通达信 PYPlugins/user 目录不存在: {user_dir}")
        if not dll_path.is_file():
            raise RuntimeError(f"通达信 TPythClient.dll 不存在: {dll_path}")

        user_str = str(user_dir.resolve())
        if user_str not in sys.path:
            sys.path.insert(0, user_str)

        from tqcenter import tq  # type: ignore[import-not-found]

        if not _tq_initialized:
            tq.initialize(self._init_path, dll_path=str(dll_path.resolve()))
            _tq_initialized = True

        _tq_module = tq
        return tq

    @staticmethod
    def normalize_stock_codes(ts_code: str | list[str]) -> list[str]:
        if isinstance(ts_code, str):
            codes = [ts_code.strip()]
        else:
            codes = [c.strip() for c in ts_code if c and str(c).strip()]

        if not codes:
            raise ValueError("stock_list 不能为空")

        for code in codes:
            if not _STOCK_CODE_PATTERN.match(code):
                raise ValueError(f"证券代码格式异常: {code!r}（示例: 600519.SH）")
        return codes

    @property
    def tq(self) -> Any:
        return self._ensure_tq()

    def get_market_data(
        self,
        *,
        field_list: list[str] | None = None,
        stock_list: list[str],
        period: str,
        start_time: str = "",
        end_time: str = "",
        count: int = -1,
        dividend_type: str | None = "none",
        fill_data: bool = True,
    ) -> dict[str, pd.DataFrame]:
        raw = self.tq.get_market_data(
            field_list=field_list or [],
            stock_list=stock_list,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=dividend_type,
            fill_data=fill_data,
        )

        if not raw:
            return {}

        if "error" in raw:
            msg = raw.get("msg", raw.get("error"))
            raise RuntimeError(f"通达信 get_market_data 失败: {msg}")

        return {k: v for k, v in raw.items() if isinstance(v, pd.DataFrame)}

    def close(self) -> None:
        global _tq_initialized, _tq_module
        if _tq_module is not None and _tq_initialized:
            _tq_module.close()
            _tq_initialized = False
