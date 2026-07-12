from src.common.setting import settings
import sys
import tushare
import pandas as pd
from typing import Type, Any, List
import json
import requests
import urllib3
from functools import partial
from tushare.pro.client import DataApi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class _DataApiWithSSLVerify(DataApi):
    """支持 SSL 证书校验开关的 DataApi 子类（第三方镜像自签证书时需关闭）。"""

    def __init__(self, token: str, timeout: int = 30, *, verify: bool = True):
        super().__init__(token=token, timeout=timeout)
        self._verify = verify

    def query(self, api_name, fields='', **kwargs):
        kwargs.setdefault('ts_type_name', self._DataApi__http_url)
        req_params = {
            'api_name': api_name,
            'token': self._DataApi__token,
            'params': kwargs,
            'fields': fields
        }
        res = requests.post(
            f"{self._DataApi__http_url}/{api_name}",
            json=req_params,
            timeout=self._DataApi__timeout,
            verify=self._verify,
        )
        if res:
            result = json.loads(res.text)
            if result['code'] != 0:
                raise Exception(result['msg'])
            data = result['data']
            columns = data['fields']
            items = data['items']
            return pd.DataFrame(items, columns=columns)
        else:
            return pd.DataFrame()

    def __getattr__(self, name):
        return partial(self.query, name)


class _RoutingDataApi:
    """按 config/tushare_api_channels.json 为每个 api_name 选择 official / stocktoday。"""

    def __init__(
        self,
        official: DataApi,
        stocktoday: DataApi | None,
        *,
        default_channel: str = "official",
    ) -> None:
        self._official = official
        self._stocktoday = stocktoday
        self._default_channel = (default_channel or "official").strip().lower()

    def _pick(self, api_name: str) -> DataApi:
        from src.common.tushare_channel_config import resolve_channel

        default: str = "official"
        if self._default_channel in ("official", "stocktoday"):
            default = self._default_channel
        ch = resolve_channel(api_name, default=default)  # type: ignore[arg-type]
        if ch == "stocktoday" and self._stocktoday is not None:
            return self._stocktoday
        return self._official

    def query(self, api_name, fields="", **kwargs):
        return self._pick(api_name).query(api_name, fields=fields, **kwargs)

    def __getattr__(self, name):
        return partial(self.query, name)


class _FallbackDataApi:
    """stocktoday 失败时降级到 official waditu。"""

    def __init__(self, primary: DataApi, fallback: DataApi | None) -> None:
        self._primary = primary
        self._fallback = fallback

    def query(self, api_name, fields="", **kwargs):
        try:
            return self._primary.query(api_name, fields=fields, **kwargs)
        except Exception as exc:
            if self._fallback is None:
                raise
            print(
                f"[tushare] 主通道失败 ({exc})，降级 official...",
                file=sys.stderr,
                flush=True,
            )
            return self._fallback.query(api_name, fields=fields, **kwargs)

    def __getattr__(self, name):
        return partial(self.query, name)


def _build_data_api(*, token: str, url: str, ssl_verify: bool, timeout: int | None = None) -> DataApi:
    req_timeout = timeout if timeout is not None else settings.tushare_timeout
    if not ssl_verify:
        ts = _DataApiWithSSLVerify(token=token, verify=False, timeout=req_timeout)
        ts._DataApi__http_url = url
        return ts
    tushare.set_token(token)
    ts = tushare.pro_api(timeout=req_timeout)
    ts._DataApi__http_url = url
    return ts


def filter_data_by_index(
    df: pd.DataFrame,
    index_columns: List[str],
    filter_column: str,
    filter_rule: str = "max",
    verbose: bool = False,
    max_display_rows: int = 50,
) -> pd.DataFrame:
    """
    根据联合索引和过滤规则，过滤掉重复数据，每组索引只保留一条记录。

    Args:
        df: tushare 返回的 DataFrame 数据
        index_columns: 联合索引的字段列表，如 ['ts_code', 'end_date', 'report_type', 'update_flag']
        filter_column: 用于过滤的字段名（如日期字段 ann_date、f_ann_date）
        filter_rule: 过滤规则，默认 "max" 表示保留该字段取值最大的那一条（如日期最大即最新）；
            "min" 表示保留该字段取值最小的那一条
        verbose: 当存在重复行时，是否按「相同索引」分组打印，并标记 [保留] / [删除]
        max_display_rows: verbose 为 True 时，最多打印多少组重复索引，默认 50；None 表示不限制

    Returns:
        去重后的 DataFrame，每组 index_columns 仅保留一条记录（按 filter_rule 选定）

    Example:
        >>> # 同一 ts_code + end_date + report_type + update_flag 只保留 f_ann_date 最新的一条
        >>> out = filter_data_by_index(
        ...     df=report_df,
        ...     index_columns=['ts_code', 'end_date', 'report_type', 'update_flag'],
        ...     filter_column='f_ann_date',
        ...     filter_rule='max',
        ...     verbose=True
        ... )
    """
    if df.empty:
        return df.copy()

    missing = [c for c in index_columns + [filter_column] if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame 中缺少列: {missing}")

    if filter_rule == "max":
        idx_keep = df.groupby(index_columns, dropna=False)[filter_column].idxmax()
    elif filter_rule == "min":
        idx_keep = df.groupby(index_columns, dropna=False)[filter_column].idxmin()
    else:
        raise ValueError(f"不支持的 filter_rule: {filter_rule}，仅支持 'max' 或 'min'")

    kept_indices = idx_keep.values
    result = df.loc[kept_indices].copy()
    result = result.reset_index(drop=True)

    n_removed = len(df) - len(result)
    if n_removed > 0 and verbose:
        print(f"\n[信息] 按联合索引去重：保留 {len(result)} 条，删除 {n_removed} 条（联合索引: {index_columns}，规则: 保留 {filter_column} {filter_rule}）")
        print("-" * 60)
        shown = 0
        for key, group_df in df.groupby(index_columns, dropna=False):
            if len(group_df) <= 1:
                continue
            if max_display_rows is not None and shown >= max_display_rows:
                print(f"\n... 仅显示前 {max_display_rows} 组重复，其余省略")
                break
            kept_idx = idx_keep[key]
            key_str = ", ".join(f"{k}={key[i]}" for i, k in enumerate(index_columns))
            print(f"\n【相同索引】 {key_str}")
            for idx in group_df.index:
                row = df.loc[idx:idx]
                if idx == kept_idx:
                    print("  [保留]")
                else:
                    print("  [删除]")
                # 只打印关键列，避免过长：联合索引 + filter_column（去重且保持顺序）
                show_cols = list(dict.fromkeys(index_columns + [filter_column]))
                show_cols = [c for c in show_cols if c in row.columns]
                print(row[show_cols].to_string(index=False))
            shown += 1

    return result


class TushareClient:
    def __init__(self):
        official = _build_data_api(
            token=settings.tushare_api_key,
            url=settings.tushare_api_url,
            ssl_verify=settings.tushare_ssl_verify,
        )
        stocktoday_key = (settings.tushare_stocktoday_api_key or "").strip()
        stocktoday: DataApi | None = None
        if stocktoday_key:
            stocktoday = _build_data_api(
                token=stocktoday_key,
                url=settings.tushare_stocktoday_api_url,
                ssl_verify=False,
            )
        default_channel = settings.tushare_channel.strip().lower()
        self._ts = _RoutingDataApi(
            official,
            stocktoday,
            default_channel=default_channel,
        )

    @property
    def ts(self):
        return self._ts
