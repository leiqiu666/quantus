"""通达信 TQ HTTP 客户端，供 ETL 等模块通过 API 中转调用。"""

from __future__ import annotations

import re

import httpx
import pandas as pd

from src.common.setting import settings
from src.common.tdx_codec import parse_market_data_payload

_STOCK_CODE_PATTERN = re.compile(r"^[0-9A-Za-z-]+\.[A-Z]{2,3}$")


class TdxClient:
    """通过 quantus-api /api/admin/tdx/{function_name} 调用通达信 tq。"""

    def __init__(self) -> None:
        self._base_url = settings.tdx_api_base_url.rstrip("/")
        self._timeout = float(settings.tdx_api_timeout)

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

    def _post(self, function_name: str, params: dict) -> object:
        url = f"{self._base_url}/api/admin/tdx/{function_name}"
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json=params)
            response.raise_for_status()
            body = response.json()
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

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
        """
        调用通达信 get_market_data，返回字段名 -> DataFrame 的字典。

        详见: https://help.tdx.com.cn/quant/docs/markdown/mindoc-1ctuhthaq5qmg/mindoc-1h10g60jt68sc.html
        """
        payload = self._post(
            "get_market_data",
            {
                "field_list": field_list or [],
                "stock_list": stock_list,
                "period": period,
                "start_time": start_time,
                "end_time": end_time,
                "count": count,
                "dividend_type": dividend_type,
                "fill_data": fill_data,
            },
        )
        return parse_market_data_payload(payload)

    def close(self) -> None:
        return None
