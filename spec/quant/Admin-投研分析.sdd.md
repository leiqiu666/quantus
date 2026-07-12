# SDD · Admin · 投研分析

> **状态：** 已实现  
> **菜单：** 投研分析（一级）  
> **依赖：** FactorDataset / KlineDataset / backtest 落盘 / 可选 TDX  
> **源码：** `src/web/admin/src/pages/research/`；`src/api/routers/admin/research.py`；`src/service/research/research_query_service.py`

---

## 1. 概述

个人用投研工作台：看截面、看个股日线、钻回测成交持仓、看单票行情快照。

**非目标：** 实盘下单、分钟线全历史、自选云同步、全市场盯盘墙。

---

## 2. 路由

```tsx
{
  path: '/research',
  name: '投研分析',
  children: [
    { path: '/research/factor-cs', name: '因子截面' },
    { path: '/research/stock-kline', name: '个股K线' },
    { path: '/research/backtest-trades', name: '回测明细' },
    { path: '/research/quote', name: '行情快照' },
  ],
}
```

---

## 3. 页面

### 3.1 因子截面

选因子或 `combo_id` + 交易日 → 截面表（ts_code, value, rank）+ 分位摘要。

### 3.2 个股K线

`ts_code` + 区间 → 日 K 蜡烛+成交量；可选 `factor_name` 右轴叠加。

### 3.3 回测明细

`run_id` → Tab：portfolio / trades / returns；支持筛选。可从回测历史跳入 `?run_id=`。

### 3.4 行情快照

单票查询：TDX 开启则代理快照；否则最近日 K + 文案「非盘中实时」。自选仅 `localStorage`。

---

## 4. API 索引

见 [`投研-因子截面与个股K线.sdd.md`](../api/admin/投研-因子截面与个股K线.sdd.md)、[`回测-明细表.sdd.md`](../api/admin/回测-明细表.sdd.md)。
