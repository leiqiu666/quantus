# SDD · Admin · 特征管理页面

> **路由：** `/quant/feature-list`  
> **菜单：** 因子管理 → 特征管理（第一位）  
> **依赖 API：** 见 [`spec/api/admin/特征-特征列表.sdd.md`](../api/admin/特征-特征列表.sdd.md)  
> **源码：** `src/web/admin/src/pages/quant/FeatureList/index.tsx`  
> **领域 SDD：** [`spec/quant/特征目录.sdd.md`](./特征目录.sdd.md)

---

## 1. 概述

展示 `feature_meta`：公式可用符号、数据源、覆盖区间。不物化特征值。

操作：
- **初始化种子**：写入国泰 panel 符号
- **刷新覆盖**：扫描日 K / 指数仓库写回起止日
- **编辑**：中文名 / 启用 / 备注 / 派生公式等
