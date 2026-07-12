"""K 线 Extract 层：读取数据源规则，按优先级调用 Client 并降级。

三个维度（daily / adj_factor / stk_limit）× 两种访问模式（按 ts_code 区间 / 按 trade_date 全市场）
共享同一份「数据源链 + 降级 + 有效性校验」实现，每个维度只声明 data_key、Client 方法名、is_usable。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
from tqdm import tqdm

from src.etl.client.kline.kline_common import (
    is_usable_kline_adj_factor,
    is_usable_kline_daily,
    is_usable_kline_stk_limit,
)
from src.etl.client.kline.kline_protocol import NotSupportedError
from src.etl.client.kline.kline_tdx_quant_client import TdxQuantKlineClient
from src.etl.client.kline.kline_tushare_client import TushareKlineClient
from src.service.etl.data_source_config_service import DataSourceConfigService

_CLIENT_CLASSES: dict[str, type[TushareKlineClient | TdxQuantKlineClient]] = {
    "tushare": TushareKlineClient,
    "tdx_quant": TdxQuantKlineClient,
}


@dataclass(frozen=True)
class _KlineExtractSpec:
    """单维度 × 单访问模式的 Extract 规格。"""

    data_key: str
    client_method_name: str
    is_usable: Callable[[pd.DataFrame], bool]


_RANGE_SPECS: dict[str, _KlineExtractSpec] = {
    "daily": _KlineExtractSpec(
        data_key="kline_daily",
        client_method_name="pull_kline_daily_range",
        is_usable=is_usable_kline_daily,
    ),
    "adj_factor": _KlineExtractSpec(
        data_key="kline_adj_factor",
        client_method_name="pull_kline_adj_factor_range",
        is_usable=is_usable_kline_adj_factor,
    ),
    "stk_limit": _KlineExtractSpec(
        data_key="kline_stk_limit",
        client_method_name="pull_kline_stk_limit_range",
        is_usable=is_usable_kline_stk_limit,
    ),
}

_BY_DATE_SPECS: dict[str, _KlineExtractSpec] = {
    "daily": _KlineExtractSpec(
        data_key="kline_daily_by_date",
        client_method_name="pull_kline_daily_by_trade_date",
        is_usable=is_usable_kline_daily,
    ),
    "adj_factor": _KlineExtractSpec(
        data_key="kline_adj_factor_by_date",
        client_method_name="pull_kline_adj_factor_by_trade_date",
        is_usable=is_usable_kline_adj_factor,
    ),
    "stk_limit": _KlineExtractSpec(
        data_key="kline_stk_limit_by_date",
        client_method_name="pull_kline_stk_limit_by_trade_date",
        is_usable=is_usable_kline_stk_limit,
    ),
}

_DATA_KEYS = tuple(s.data_key for s in (*_RANGE_SPECS.values(), *_BY_DATE_SPECS.values()))


class KlineExtract:
    """K 线 Extract：读数据源配置，按优先级调用 Client 并降级。"""

    def __init__(self) -> None:
        self.config = DataSourceConfigService()
        self.config.seed_defaults_if_empty()
        self.config.seed_missing_defaults()
        for key in _DATA_KEYS:
            self.config.sync_priorities_from_settings(key)
        self.clients: dict[str, TushareKlineClient | TdxQuantKlineClient] = {}
        self._source_chain_cache: dict[str, list[str]] = {}

    # ---------- 内部统一实现 ----------

    def _get_source_chain(self, data_key: str) -> list[str]:
        if data_key not in self._source_chain_cache:
            chain = self.config.get_source_chain(
                data_key, allowed_sources=_CLIENT_CLASSES.keys()
            )
            self._source_chain_cache[data_key] = chain
            if chain:
                tqdm.write(f"[信息] {data_key} 数据源链: {' → '.join(chain)}")
        return self._source_chain_cache[data_key]

    def _pull_with_chain(
        self,
        spec: _KlineExtractSpec,
        *,
        call_kwargs: dict,
    ) -> pd.DataFrame:
        """按数据源链顺序调用 Client；不支持/异常/无效则降级到下一源。"""
        chain = self._get_source_chain(spec.data_key)
        if not chain:
            tqdm.write(f"[警告] {spec.data_key} 无可用数据源配置")
            return pd.DataFrame()

        last_error: Exception | None = None
        for source in chain:
            try:
                client = self.get_client(source)
                method = getattr(client, spec.client_method_name)
                df = method(**call_kwargs)
            except NotSupportedError as exc:
                tqdm.write(f"[警告] {spec.data_key} 数据源 {source} 不支持: {exc}")
                last_error = exc
                continue
            except Exception as exc:
                tqdm.write(f"[警告] {spec.data_key} 数据源 {source} 调用失败: {exc}")
                last_error = exc
                continue

            if spec.is_usable(df):
                return df

            tqdm.write(f"[警告] {spec.data_key} 数据源 {source} 返回空或无效，尝试下一源")

        if last_error is not None:
            tqdm.write(
                f"[错误] {spec.data_key} 全部数据源失败，最后错误: {last_error}"
            )
        else:
            tqdm.write(f"[错误] {spec.data_key} 全部数据源返回空或无效数据")
        return pd.DataFrame()

    # ---------- 公开 6 方法（薄壳） ----------

    def pull_kline_daily_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_with_chain(
            _RANGE_SPECS["daily"],
            call_kwargs={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        )

    def pull_kline_adj_factor_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_with_chain(
            _RANGE_SPECS["adj_factor"],
            call_kwargs={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        )

    def pull_kline_stk_limit_range(
        self, *, ts_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        return self._pull_with_chain(
            _RANGE_SPECS["stk_limit"],
            call_kwargs={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        )

    def pull_kline_daily_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_with_chain(
            _BY_DATE_SPECS["daily"], call_kwargs={"trade_date": trade_date}
        )

    def pull_kline_adj_factor_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_with_chain(
            _BY_DATE_SPECS["adj_factor"], call_kwargs={"trade_date": trade_date}
        )

    def pull_kline_stk_limit_by_date(self, *, trade_date: str) -> pd.DataFrame:
        return self._pull_with_chain(
            _BY_DATE_SPECS["stk_limit"], call_kwargs={"trade_date": trade_date}
        )

    def get_client(self, source: str) -> TushareKlineClient | TdxQuantKlineClient:
        """懒加载 Client 实例（同 Extract 内复用）。"""
        if source not in self.clients:
            cls = _CLIENT_CLASSES.get(source)
            if cls is None:
                raise ValueError(f"未注册 K 线数据源: {source}")
            self.clients[source] = cls()
        return self.clients[source]
