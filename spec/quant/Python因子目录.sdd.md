# SDD · Python 复杂因子目录

> **目录：** `src/research/factor/python/`  
> **注册：** `FactorRegistry.auto_discover()` 扫包（含本目录）  
> **Admin：** 只读展示源码（见 [`Admin-因子管理.sdd.md`](./Admin-因子管理.sdd.md)）

---

## 1. 约定

- **所有复杂 Python 因子**（`BaseFactor` 子类）只放在 `src/research/factor/python/`
- 禁止再放到 `price_volume/`、`gtja/` 等其它业务包内作为自研 compute 实现
- 国泰公式引擎仍在 `gtja/`；其产出因子 `impl_kind=formula`，不是本目录文件

---

## 2. 迁移清单

| 因子 | 原路径 | 新路径 |
|------|--------|--------|
| `momentum_20d` | `factor/price_volume/momentum.py` | `factor/python/momentum.py` |
| `volatility_60d` | `factor/price_volume/volatility.py` | `factor/python/volatility.py` |

迁完后删除空的 `price_volume/` 包。

---

## 3. 元数据

`update-meta` 写入：

- `source=自研`
- `impl_kind=python`
- `python_path=src/research/factor/python/<module>.py`（相对仓库根）

---

## 4. Admin 源码

- `GET /api/admin/quant/factor/{name}/source`
- 路径必须 resolve 后落在 `src/research/factor/python/` 下（白名单）
- **只读**，不写回磁盘
