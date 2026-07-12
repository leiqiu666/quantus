# SDD · 投研 · 因子截面与个股K线 / 行情快照

> **HTTP：**  
> - `GET /api/admin/research/factor-cs`  
> - `GET /api/admin/research/stock-kline`  
> - `GET /api/admin/research/quote`  
> **模式：** ① Service 读  
> **源码：** `src/api/routers/admin/research.py`

---

## 1. 因子截面

Query：`factor_name` 或 `combo_id`（二选一）、`trade_date`（YYYYMMDD）。

响应：

```json
{
  "trade_date": "20260529",
  "factor_name": "gtja_alpha1",
  "rows": [{"ts_code": "000001.SZ", "value": 0.1, "rank": 1}],
  "quantiles": {"p10": ..., "p50": ..., "p90": ..., "count": N}
}
```

组合：现场 z-score 加权（同 MultiFactorStrategy），`factor_name` 返回组合名。

---

## 2. 个股K线

Query：`ts_code`、`start`、`end`、可选 `factor_name`。

响应：`bars: [{trade_date, open, high, low, close, vol, amount, close_adj?}]`，若有因子则 `factor: [{trade_date, value}]`。

优先 Parquet `KlineDataset`；空则降级 PG `kline_daily`。

---

## 3. 行情快照

Query：`ts_code`。

响应：

```json
{
  "mode": "tdx" | "daily",
  "ts_code": "...",
  "trade_date": "...",
  "price": ...,
  "pre_close": ...,
  "change_pct": ...,
  "open": ..., "high": ..., "low": ..., "close": ..., "vol": ...,
  "message": "日线快照，非盘中实时"
}
```

`TDX_QUANT_ENABLED=false` 时 `mode=daily`；TDX 失败同样降级日线并带 message。
