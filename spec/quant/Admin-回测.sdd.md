# SDD · Admin · 回测与因子组合

> **状态：** 已实现（含增强：成本/基准/告警/分组柱/换手/分年）  
> **菜单：** 回测管理 → 回测 / 因子组合  
> **依赖：** [`截面回测.sdd.md`](./截面回测.sdd.md)、[`回测-运行与结果.sdd.md`](../api/admin/回测-运行与结果.sdd.md)、[`回测-因子组合.sdd.md`](../api/admin/回测-因子组合.sdd.md)  
> **源码：** `src/web/admin/src/pages/quant/Backtest/`、`FactorCombo/`；引擎 `MultiFactorStrategy` + `BacktestRunner`

---

## 1. 概述

在 Admin 提供截面回测入口：单因子 / 多因子组合；SSE `backtest_run`；结果 `warehouse/backtest/` + PG `backtest_run`。

**非目标：** 实盘下单、合成因子物化、行业/市值中性、事件驱动。

---

## 2. 路由与菜单

回测管理：`/quant/factor-list`、`/quant/factor-combo`、`/quant/backtest`。  
明细钻取见「投研分析 → 回测明细」。

---

## 3. 页面

### 3.1 回测发起

参数：区间、调仓、分组、**佣金/印花税/滑点**（默认万三 / 卖出千一 / 0）。基准固定 `000300.SH`（不可改）。

### 3.2 详情 Drawer

- 指标卡 + warnings Alert  
- 净值曲线：多空 / top / bottom / **基准** / 超额（多空−基准）  
- 分组累计收益柱状图  
- 调仓换手折线  
- 分年度绩效表  
- IC 时序 + summary JSON  
- 链到 `/research/backtest-trades?run_id=`

---

## 4. 多因子合成

同前：截面 z-score 加权；配方只存 PG。

---

## 5. 验收

1. 改佣金两次回测摘要可区分  
2. 详情有基准线与 warnings  
3. 分组柱 / 换手 / 分年表有数据（短样本时分年可能仅 1 行）
