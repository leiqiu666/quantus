# SDD · Admin · 因子管理页面

> **路由：** `/quant/factor-list`
> **菜单：** 量化交易 → 因子管理
> **依赖 API：** `GET /api/admin/quant/factor/list`（见 [`spec/api/admin/因子-因子列表.sdd.md`](../api/admin/因子-因子列表.sdd.md)）
> **源码：** `src/web/admin/src/pages/quant/FactorList/index.tsx`

---

## 1. 概述

在 Admin 后台新增「量化交易」一级菜单，下设「因子管理」页面。展示系统中所有可用因子（自研 + Tushare），包括名称、来源、分类、算法、数据覆盖区间。

---

## 2. 路由配置

在 `routes.config.tsx` 新增：

```tsx
{
  path: '/quant',
  name: '量化交易',
  icon: <StockOutlined />,
  children: [
    {
      path: '/quant/factor-list',
      name: '因子管理',
      element: <FactorList />,
    },
  ],
},
```

---

## 3. 页面设计

### 3.1 ProTable 列表

| 列 | 字段 | 宽度 | 筛选 | 说明 |
|----|------|------|------|------|
| 因子名称 | factor_name | 180 | - | 代码中使用的名称 |
| 中文名 | display_name | 200 | - | 可读描述 |
| 来源 | source | 80 | 下拉筛选 | `自研` / `tushare` |
| 分类 | category | 100 | 下拉筛选 | 基本面 / 技术 / 量价 / 统计 |
| 算法 | formula | 250 | - | 计算规则说明 |
| 起始日 | start_date | 100 | - | Parquet 最早日 |
| 截止日 | end_date | 100 | - | Parquet 最晚日 |
| 月份数 | month_count | 80 | - | 已有分区数 |

### 3.2 筛选栏

- 来源：ValueEnum 下拉（自研 / tushare / 全部）
- 分类：ValueEnum 下拉（基本面 / 技术 / 量价 / 统计 / 全部）
- 搜索按钮 + 重置按钮

### 3.3 无分页

因子总数 ~100 个，全量返回，前端不分页。`search: false` 或 ProTable 内置筛选即可。

---

## 4. 文件清单

```
src/web/admin/src/
  pages/quant/
    FactorList/
      index.tsx              # ProTable 页面组件
  services/
    quant.ts                 # getFactorList API 调用
  types/
    quant.ts                 # FactorMetaItem 类型定义
  routes/
    routes.config.tsx        # +量化交易菜单
```

---

## 5. 验收

1. 左侧菜单出现「量化交易 → 因子管理」
2. 点击进入看到 95 个因子列表
3. 按来源筛选 `tushare` → 显示 93 个
4. 按分类筛选 `基本面` → 显示基本面因子
