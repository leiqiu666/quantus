# SDD · Admin · 因子列表与编辑 / 生成

> **路由：** `/quant/factor-list`  
> **菜单：** 因子管理 → 因子列表  
> **依赖：**  
> - [`因子-因子列表.sdd.md`](../api/admin/因子-因子列表.sdd.md)  
> - [`因子-编辑与源码.sdd.md`](../api/admin/因子-编辑与源码.sdd.md)  
> - [`因子-生成-SSE.sdd.md`](../api/admin/因子-生成-SSE.sdd.md)  
> **源码：** `src/web/admin/src/pages/quant/FactorList/index.tsx`  
> **相关：** [`Python因子目录.sdd.md`](./Python因子目录.sdd.md)

---

## 1. 概述

展示 `factor_meta`（分页）。按 `impl_kind` 提供编辑与生成：

| impl_kind | 编辑 | 生成 |
|-----------|------|------|
| `formula` | 可改公式 → PG；计算优先 DB | SSE `factor_compute`（国泰按名） |
| `python` | 只读展示 `factor/python/*.py` | SSE `factor_compute`（自研 Strategy） |
| `tushare` | 只读映射说明 | 按钮禁用（走 Research CLI） |

---

## 2. 菜单

1. 特征管理 `/quant/feature-list`
2. 因子列表 `/quant/factor-list`
3. 因子组合
4. 回测

---

## 3. 页面行为

### 3.1 列表

- 列：名称、中文名、来源、impl_kind、分类、公式摘要、覆盖起止、月份数
- 筛选：source / category / keyword；分页默认 20
- 操作：编辑、生成、回测（有覆盖时）

### 3.2 编辑 Drawer

- **formula**：可视化公式编辑器（特征点选 / 运算符号 / 常用函数 / 拖拽）→ 保存 `PUT /factor/{name}`
- **python**：只读代码 + `python_path` 提示（`GET .../source`）
- **tushare**：只读 `formula` / display_name

### 3.3 生成

- 弹窗：起止日期（或按月）、force 覆盖已有月份
- SSE `task_key=factor_compute`，参数 `factor_name`、`start_date`、`end_date`、`force`
- 国泰整批仍可用页头「计算国泰191」→ `gtja191_compute`

---

## 4. 存储（因子值）

权威：`{WAREHOUSE_ROOT}/factor/{factor_name}/dt=YYYYMM/` 长表 `ts_code, trade_date, value`。  
元数据：PG `factor_meta`（含 `impl_kind`、`python_path`、`formula`）。  
热层：`factor_latest`。详见 [`量化层完整方案.md`](../../docs/量化层完整方案.md)。
