"""巨潮资讯网（cninfo）HTTP 客户端，供其他模块调用。"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

# 与 szse_stock.json 返回字段一致，空结果时仍保持列名便于下游拼接
_STOCK_LIST_COLUMNS = ["code", "pinyin", "category", "orgId", "zwjc"]

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class CninfoClient:
    DEFAULT_SZSE_STOCK_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        stock_list_url: str | None = None,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout = timeout
        self._stock_list_url = stock_list_url or self.DEFAULT_SZSE_STOCK_URL
        self._user_agent = user_agent

    def _get_json(self, url: str) -> dict:
        req = Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                code = resp.getcode()
                if code != 200:
                    raise RuntimeError(f"cninfo HTTP {code}: {url}")
                raw = resp.read().decode("utf-8")
        except HTTPError as e:
            raise RuntimeError(f"cninfo HTTP {e.code}: {url}") from e
        except URLError as e:
            raise RuntimeError(f"cninfo 请求失败: {e.reason!s}") from e

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"cninfo 响应非合法 JSON: {url}") from e

        if not isinstance(data, dict):
            raise ValueError(f"cninfo 响应 JSON 根节点须为 object: {url}")
        return data

    def stock_list(self) -> pd.DataFrame:
        """
        GET 巨潮股票列表（szse_stock.json），解析顶层 stockList 为 DataFrame。

        若缺少 stockList 或类型非 list，返回同列名的空表。
        """
        data = self._get_json(self._stock_list_url)
        rows = data.get("stockList")
        if not isinstance(rows, list):
            return pd.DataFrame(columns=_STOCK_LIST_COLUMNS)
        if not rows:
            return pd.DataFrame(columns=_STOCK_LIST_COLUMNS)
        return pd.DataFrame(rows)


if __name__ == "__main__":
    df = CninfoClient().stock_list()
    print(f"rows={len(df)}")
    print(df.head())
