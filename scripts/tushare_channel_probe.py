#!/usr/bin/env python3
"""Tushare 渠道连通性探测：独立于 ETL，验证 .env 配置与第三方套壳是否可用。

用法：
    uv run python scripts/tushare_channel_probe.py
    uv run python scripts/tushare_channel_probe.py --rounds 10 --api moneyflow_hsgt
    uv run python scripts/tushare_channel_probe.py --channel official
    uv run python scripts/tushare_channel_probe.py --list-apis

探测项：
  1. DNS 解析
  2. stocktoday / official 直连 HTTP（绕过 Fallback）
  3. 项目 TushareClient（含 stocktoday→official 降级）
  4. 可选连续压测（模拟 SSE 补位逐日调用）
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import requests

from src.common.setting import settings
from src.common.tushare_client import TushareClient, _build_data_api

# 项目已接入、且覆盖 P0 的代表性接口
DEFAULT_APIS: dict[str, dict[str, Any]] = {
    "moneyflow_hsgt": {"trade_date": "20250102"},
    "daily_basic": {"trade_date": "20250102"},
    "moneyflow": {"trade_date": "20250102"},
    "trade_cal": {"exchange": "SSE", "start_date": "20250101", "end_date": "20250110"},
    "stock_basic": {"list_status": "L"},
    "index_basic": {"market": "SSE"},
    "index_daily": {"ts_code": "000300.SH", "start_date": "20250102", "end_date": "20250103"},
    "hk_hold": {"trade_date": "20250102"},
    "stk_premarket": {"trade_date": "20240603"},
    "top10_holders": {"ann_date": "20240430"},
    "disclosure_date": {"end_date": "20241231"},
}


@dataclass
class ProbeResult:
    api: str
    channel: str
    ok: bool
    rows: int
    ms: float
    detail: str


def _mask_token(token: str) -> str:
    token = (token or "").strip()
    if len(token) <= 10:
        return "(empty)"
    return f"{token[:6]}...{token[-4:]}"


def _host_from_url(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").split("/")[0]


def print_config() -> None:
    print("=" * 60)
    print("当前 .env → settings 映射")
    print("=" * 60)
    print(f"  TUSHARE_CHANNEL          = {settings.tushare_channel}")
    print(f"  TUSHARE_STOCKTODAY_URL   = {settings.tushare_stocktoday_api_url}")
    print(f"  TUSHARE_STOCKTODAY_KEY   = {_mask_token(settings.tushare_stocktoday_api_key)}")
    print(f"  TUSHARE_API_URL          = {settings.tushare_api_url}")
    print(f"  TUSHARE_API_KEY          = {_mask_token(settings.tushare_api_key)}")
    print(f"  TUSHARE_SSL_VERIFY       = {settings.tushare_ssl_verify}")
    print(f"  TUSHARE_RETRY_MAX        = {settings.tushare_retry_max}  (也读 TUSHARE_RETRY_COUNT)")
    print(f"  TUSHARE_RETRY_INTERVAL   = {settings.tushare_retry_interval}")
    print(f"  TUSHARE_TIMEOUT          = {settings.tushare_timeout}")
    if settings.tushare_channel.strip().lower() == "stocktoday":
        print("  行为: 主通道 stocktoday 失败 → 自动降级 official waditu")
    print()


def probe_dns(url: str) -> tuple[bool, str]:
    host = _host_from_url(url)
    try:
        ip = socket.gethostbyname(host)
        return True, f"{host} → {ip}"
    except OSError as exc:
        return False, f"{host} DNS 失败: {exc}"


def raw_http_probe(
    *,
    base_url: str,
    token: str,
    api_name: str,
    params: dict[str, Any],
    verify: bool,
    timeout: int,
) -> ProbeResult:
    url = f"{base_url.rstrip('/')}/{api_name}"
    payload = {
        "api_name": api_name,
        "token": token,
        "params": params,
        "fields": "",
    }
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=timeout, verify=verify)
        ms = (time.perf_counter() - t0) * 1000
        if resp.status_code != 200:
            return ProbeResult(api_name, "http", False, 0, ms, f"HTTP {resp.status_code}")
        body = resp.json()
        code = body.get("code")
        msg = body.get("msg") or ""
        if code != 0:
            return ProbeResult(api_name, "http", False, 0, ms, f"API code={code} {msg[:120]}")
        rows = len(body.get("data", {}).get("items") or [])
        return ProbeResult(api_name, "http", True, rows, ms, "OK")
    except requests.exceptions.RequestException as exc:
        ms = (time.perf_counter() - t0) * 1000
        return ProbeResult(api_name, "http", False, 0, ms, f"{type(exc).__name__}: {exc}")


def client_probe(api_name: str, params: dict[str, Any], channel: str) -> ProbeResult:
    ch = channel.strip().lower()
    if ch == "stocktoday":
        primary = _build_data_api(
            token=settings.tushare_stocktoday_api_key,
            url=settings.tushare_stocktoday_api_url,
            ssl_verify=False,
            timeout=settings.tushare_timeout,
        )
        fallback = _build_data_api(
            token=settings.tushare_api_key,
            url=settings.tushare_api_url,
            ssl_verify=settings.tushare_ssl_verify,
            timeout=settings.tushare_timeout,
        )
        from src.common.tushare_client import _FallbackDataApi

        ts = _FallbackDataApi(primary, fallback)
        label = "client(stocktoday+fallback)"
    elif ch == "official":
        ts = _build_data_api(
            token=settings.tushare_api_key,
            url=settings.tushare_api_url,
            ssl_verify=settings.tushare_ssl_verify,
            timeout=settings.tushare_timeout,
        )
        label = "client(official)"
    else:
        ts = TushareClient().ts
        label = f"client({settings.tushare_channel})"

    fn = getattr(ts, api_name)
    t0 = time.perf_counter()
    try:
        df = fn(**params)
        ms = (time.perf_counter() - t0) * 1000
        n = len(df) if isinstance(df, pd.DataFrame) else 0
        return ProbeResult(api_name, label, True, n, ms, "OK")
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000
        return ProbeResult(api_name, label, False, 0, ms, f"{type(exc).__name__}: {exc}")


def _print_row(r: ProbeResult) -> None:
    mark = "✓" if r.ok else "✗"
    print(f"  {mark} {r.api:20s} [{r.channel:22s}] rows={r.rows:5d} {r.ms:7.0f}ms  {r.detail}")


def run_round(
    apis: dict[str, dict[str, Any]],
    *,
    channel: str,
    timeout: int,
    skip_http: bool,
) -> tuple[int, int]:
    ok = fail = 0

    if not skip_http:
        print("--- stocktoday 直连 HTTP ---")
        for name, params in apis.items():
            r = raw_http_probe(
                base_url=settings.tushare_stocktoday_api_url,
                token=settings.tushare_stocktoday_api_key,
                api_name=name,
                params=params,
                verify=False,
                timeout=timeout,
            )
            _print_row(r)
            ok += r.ok
            fail += not r.ok

        print("--- official 直连 HTTP ---")
        for name, params in apis.items():
            r = raw_http_probe(
                base_url=settings.tushare_api_url,
                token=settings.tushare_api_key,
                api_name=name,
                params=params,
                verify=settings.tushare_ssl_verify,
                timeout=timeout,
            )
            _print_row(r)
            ok += r.ok
            fail += not r.ok

    print(f"--- TushareClient ({channel}) ---")
    for name, params in apis.items():
        r = client_probe(name, params, channel)
        _print_row(r)
        ok += r.ok
        fail += not r.ok

    return ok, fail


def stress_test(api_name: str, params: dict[str, Any], rounds: int, channel: str) -> None:
    print(f"\n连续压测 {api_name} × {rounds} 轮（channel={channel}）")
    ok = fail = 0
    times: list[float] = []
    for i in range(rounds):
        r = client_probe(api_name, params, channel)
        times.append(r.ms)
        if r.ok:
            ok += 1
            print(f"  #{i + 1:3d} OK  rows={r.rows}  {r.ms:.0f}ms")
        else:
            fail += 1
            print(f"  #{i + 1:3d} FAIL {r.detail}")
        time.sleep(0.15)
    if times:
        print(f"  汇总: ok={ok} fail={fail}  latency min={min(times):.0f}ms p50={sorted(times)[len(times)//2]:.0f}ms max={max(times):.0f}ms")


def main() -> int:
    parser = argparse.ArgumentParser(description="Tushare 渠道连通性探测")
    parser.add_argument("--api", action="append", help="只测指定 API，可重复")
    parser.add_argument("--rounds", type=int, default=1, help="整轮重复次数（默认 1）")
    parser.add_argument("--stress", type=int, default=0, help="对首个 API 连续调用 N 次")
    parser.add_argument(
        "--channel",
        choices=["auto", "stocktoday", "official"],
        default="auto",
        help="TushareClient 测试渠道（auto=读 .env）",
    )
    parser.add_argument("--skip-http", action="store_true", help="跳过直连 HTTP，只测 Client")
    parser.add_argument("--list-apis", action="store_true", help="列出内置 API 并退出")
    parser.add_argument("--timeout", type=int, default=None, help="HTTP 超时秒（默认读 settings）")
    args = parser.parse_args()

    if args.list_apis:
        for name, params in DEFAULT_APIS.items():
            print(f"  {name:20s} {params}")
        return 0

    apis = DEFAULT_APIS
    if args.api:
        unknown = [a for a in args.api if a not in DEFAULT_APIS]
        if unknown:
            print(f"未知 API: {unknown}，可用 --list-apis 查看", file=sys.stderr)
            return 2
        apis = {k: DEFAULT_APIS[k] for k in args.api}

    channel = settings.tushare_channel if args.channel == "auto" else args.channel
    timeout = args.timeout if args.timeout is not None else settings.tushare_timeout

    print_config()

    for url in (settings.tushare_stocktoday_api_url, settings.tushare_api_url):
        ok, msg = probe_dns(url)
        mark = "✓" if ok else "✗"
        print(f"  {mark} DNS {msg}")
    print()

    total_ok = total_fail = 0
    for rnd in range(args.rounds):
        if args.rounds > 1:
            print(f"\n========== 第 {rnd + 1}/{args.rounds} 轮 ==========")
        ok, fail = run_round(apis, channel=channel, timeout=timeout, skip_http=args.skip_http)
        total_ok += ok
        total_fail += fail

    if args.stress > 0:
        first_api = next(iter(apis))
        stress_test(first_api, apis[first_api], args.stress, channel)

    print()
    print("=" * 60)
    if total_fail == 0:
        print(f"全部通过（{total_ok} 项）")
    else:
        print(f"存在失败：ok={total_ok} fail={total_fail}")
        print()
        print("排查提示：")
        print("  1. .env 中 TUSHARE_RETRY_COUNT 现已映射到 TUSHARE_RETRY_MAX；")
        print("     网络抖动时旧版默认重试 10000 次会导致 SSE 长时间卡住。")
        print("  2. stocktoday 主通道偶发断连会打印「降级 official」；若 official 也失败会进入重试循环。")
        print("  3. DNS 解析 tushare.citydata.club 失败多为本地网络/DNS 问题，与 API Key 无关。")
        print("  4. 若 stocktoday 直连全 OK 但 Client 失败，检查 Fallback 层 official Key 积分/限流。")
    print("=" * 60)
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
