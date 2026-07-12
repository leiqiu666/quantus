#!/usr/bin/env python3
"""从 get_tushare_doc 本地文档生成 config/tushare_api_channels.json（全量 Tushare API）。

数据源：`.claude/skills/get_tushare_doc/doc_index.json`（当前约 233 个 api_name）
       + 文档中提及但无独立索引页的 *_vip 别名（6 个）

规则（与 5000 积分官方账号对齐）：
- points_required <= 5000 且非独立开通 → channel=official
- points_required > 5000 或 separate_permission → channel=stocktoday
- official 频次取文档在 5000 积分档的描述；stocktoday 统一 100 次/分钟
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_INDEX = ROOT / ".claude/skills/get_tushare_doc/doc_index.json"
DOC_DIR = ROOT / ".claude/skills/get_tushare_doc/doc"
OUT = ROOT / "config/tushare_api_channels.json"

OFFICIAL_USER_POINTS = 5000
STOCKTODAY_RATE = 100

# Quantus 已接入 ETL 使用的 api（生成时打标 in_quantus_etl，便于检索）
QUANTUS_ETL_APIS: frozenset[str] = frozenset({
    "stock_basic", "trade_cal", "suspend_d", "daily", "adj_factor", "stk_limit",
    "stk_factor_pro", "daily_basic", "dividend", "moneyflow", "margin_detail",
    "hsgt_top10", "moneyflow_hsgt", "hk_hold", "block_trade", "top_list", "top_inst",
    "stk_holdernumber", "top10_holders", "top10_floatholders", "forecast_vip",
    "express_vip", "fina_audit", "income_vip", "balancesheet_vip", "cashflow_vip",
    "fina_indicator_vip", "income", "balancesheet", "cashflow", "fina_indicator",
    "disclosure_date", "fina_mainbz", "index_weight", "index_basic", "index_classify",
    "index_member_all", "index_daily", "stk_premarket", "share_float",
})

# 无独立 doc 索引页、但在 base 接口文档中声明的 VIP 别名
VIP_ALIAS_APIS: dict[str, str] = {
    "forecast_vip": "forecast",
    "express_vip": "express",
    "income_vip": "income",
    "balancesheet_vip": "balancesheet",
    "cashflow_vip": "cashflow",
    "fina_indicator_vip": "fina_indicator",
    "fina_mainbz_vip": "fina_mainbz",
}

# 文档解析不准时的手工覆盖（points / rate / separate / label）
MANUAL: dict[str, dict] = {
    "forecast_vip": {"label": "业绩预告VIP", "points_required": 5000, "rate_limit_official": 200},
    "express_vip": {"label": "业绩快报VIP", "points_required": 5000, "rate_limit_official": 200},
    "income_vip": {"label": "利润表VIP", "points_required": 5000, "rate_limit_official": 200},
    "balancesheet_vip": {"label": "资产负债表VIP", "points_required": 5000, "rate_limit_official": 200},
    "cashflow_vip": {"label": "现金流量表VIP", "points_required": 5000, "rate_limit_official": 200},
    "fina_indicator_vip": {"label": "财务指标VIP", "points_required": 5000, "rate_limit_official": 200},
    "fina_mainbz_vip": {"label": "主营业务构成VIP", "points_required": 5000, "rate_limit_official": 200},
    "daily": {"points_required": 120, "rate_limit_official": 500},
    "share_float": {"points_required": 120},
    "stk_factor_pro": {"rate_limit_official": 30},
    "moneyflow_hsgt": {"rate_limit_official": 500},
    "stk_premarket": {
        "label": "盘前股本",
        "points_required": 0,
        "separate_permission": True,
    },
}


def _load_index() -> dict[str, dict]:
    raw = json.loads(DOC_INDEX.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for item in raw.values():
        if isinstance(item, dict) and item.get("api_name"):
            out[item["api_name"]] = item
    return out


def _all_api_names(index: dict[str, dict]) -> list[str]:
    names = set(index.keys())
    names.update(VIP_ALIAS_APIS.keys())
    return sorted(names)


def _read_doc(api: str, index: dict[str, dict]) -> tuple[str, dict | None]:
    ref = VIP_ALIAS_APIS.get(api, api)
    item = index.get(ref)
    if item:
        path = DOC_DIR / item["filename"]
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="ignore"), item
    matches = list(DOC_DIR.glob(f"*_{ref}.md"))
    if matches:
        return matches[0].read_text(encoding="utf-8", errors="ignore"), item
    return "", item


def _parse_title(text: str, fallback: str) -> str:
    m = re.search(r'^title:\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else fallback


def _parse_points(text: str, api: str) -> int | None:
    if api.endswith("_vip"):
        m = re.search(r"(?:VIP|vip).*?(\d+)积分", text)
        if m:
            return int(m.group(1))
        m = re.search(r"需(?:积攒|要)?(\d+)积分", text)
        if m:
            return int(m.group(1))
    vals: list[int] = []
    for m in re.finditer(r"(\d+)积分", text):
        v = int(m.group(1))
        if v >= 10:
            vals.append(v)
    if not vals:
        return None
    if api.endswith("_vip"):
        high = [v for v in vals if v >= 5000]
        return max(high) if high else max(vals)
    return min(vals)


def _parse_official_rate(text: str, points: int | None) -> int:
    for pat in (
        r"5000积分.*?每分钟(?:可以请求|可提取|可)?(\d+)次",
        r"5000积分以上.*?每分钟.*?(\d+)次",
        r"基础积分每分钟可调取(\d+)次",
        r"(\d+)次/分钟",
        r"每分钟(?:可以请求|可提取|可)?(\d+)次",
    ):
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return 200


def _parse_separate_permission(text: str) -> bool:
    return bool(re.search(r"在线开通|单独开通|独立开通|weborder/#/permission", text, re.I))


def _resolve_channel(points: int | None, separate: bool) -> str:
    if separate:
        return "stocktoday"
    if points is not None and points > OFFICIAL_USER_POINTS:
        return "stocktoday"
    return "official"


def build_entry(api: str, index: dict[str, dict]) -> dict:
    manual = MANUAL.get(api, {})
    text, item = _read_doc(api, index)

    separate = manual.get("separate_permission", False)
    if not separate and text:
        separate = _parse_separate_permission(text)

    points = manual.get("points_required")
    if points is None and text:
        points = _parse_points(text, api)
    points = 2000 if points is None else points

    rate_off = manual.get("rate_limit_official")
    if rate_off is None and text:
        rate_off = _parse_official_rate(text, points)
    rate_off = rate_off or 200

    if api.endswith("_vip") and api in VIP_ALIAS_APIS:
        label = manual.get("label") or f"{_parse_title(text, api)}VIP"
    else:
        label = manual.get("label") or (_parse_title(text, api) if text else api)

    doc_id = manual.get("doc_id") or (item or {}).get("doc_id")
    channel = manual.get("channel") or _resolve_channel(points, separate)

    entry: dict = {
        "label": label,
        "points_required": points,
        "rate_limit": {
            "official": rate_off,
            "stocktoday": STOCKTODAY_RATE,
        },
        "channel": channel,
    }
    if separate:
        entry["separate_permission"] = True
    if doc_id:
        entry["doc_id"] = doc_id
    if api in VIP_ALIAS_APIS:
        entry["doc_alias"] = VIP_ALIAS_APIS[api]
    if api in QUANTUS_ETL_APIS:
        entry["in_quantus_etl"] = True
    return entry


def main() -> None:
    index = _load_index()
    api_names = _all_api_names(index)
    entries = {api: build_entry(api, index) for api in api_names}

    def sort_key(item: tuple[str, dict]) -> tuple:
        api, cfg = item
        ch_order = 0 if cfg["channel"] == "official" else 1
        pts = cfg.get("points_required") or 99999
        return (ch_order, pts, api)

    ordered = dict(sorted(entries.items(), key=sort_key))

    official = sum(1 for v in ordered.values() if v["channel"] == "official")
    stocktoday = sum(1 for v in ordered.values() if v["channel"] == "stocktoday")
    etl = sum(1 for v in ordered.values() if v.get("in_quantus_etl"))

    payload = {
        "_meta": {
            "description": "Quantus Tushare 全量接口渠道路由（doc_index + VIP 别名）",
            "official_user_points": OFFICIAL_USER_POINTS,
            "routing_rule": "<=5000积分且非独立开通→official；>5000积分或需独立开通→stocktoday",
            "stocktoday_rate_limit_per_minute": STOCKTODAY_RATE,
            "source": ".claude/skills/get_tushare_doc/doc_index.json",
            "api_count": len(ordered),
            "official_count": official,
            "stocktoday_count": stocktoday,
            "quantus_etl_count": etl,
            "regenerate": "uv run python scripts/generate_tushare_channel_config.py",
            "note": "新增 Tushare 文档后先 crawl/fetch，再跑 regenerate；手工改 channel 会被覆盖，请改 MANUAL 或生成后写回脚本",
        },
        "apis": ordered,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} — total={len(ordered)} official={official} stocktoday={stocktoday} etl={etl}")


if __name__ == "__main__":
    main()
