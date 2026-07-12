# SDD · 缺失日志 log_missing

> **模块定位：** 跨域基础设施。记录 ETL 完整性校验中发现但尚未补入库的「缺失项」，作为补拉重试的待办列表。
> **源码入口：**
> - 表实体：[`src/entities/data_entities/log_missing.py`](../../src/entities/data_entities/log_missing.py)
> - 数据访问：[`src/etl/log/missing_log.py`](../../src/etl/log/missing_log.py)
> **调用方：** [`ReportWorkflow`](../../src/etl/workflow/financial/report_workflow.py)、[`KlineWorkflow`](../../src/etl/workflow/kline/kline_workflow.py)

---

## 1. 概述

`log_missing` 是 ETL 各域共用的「未完成任务」登记表：

- **写入时机：** 完整性校验发现某 (ts_code, missing_entity, missing_date) 在 DB 中缺失，先把它登记到本表（视为「待补拉」）。
- **删除时机：** 该缺失项被成功补入对应业务表（report_*, kline_daily, …）后，**物理删除**这条登记。
- **核心不变量：** `log_missing` 表里的每一行都代表「至今仍未补入库」的缺失项；表为空 ⇔ 全部补齐。

> 历史上曾有 `last_try_result` 字段（`1`=成功，`0`=失败），用于「成功保留行 + 标记结果」。该字段连同 `idx_log_missing_last_try_result` 索引已于此次迁移**彻底删除**；当前语义统一为「**成功就删，失败留底并累计 try_count**」。

---

## 2. 数据模型

### 2.1 表结构（[`LogMissing`](../../src/entities/data_entities/log_missing.py)）

| 列 | 类型 | 含义 |
|----|------|------|
| `id` | Integer PK auto | 主键 |
| `ts_code` | String(20) | 股票代码，例 `000001.SZ` |
| `missing_entity` | String(100) | 缺失实体类型，详见 §2.2 |
| `missing_date` | String(8) | 缺失日期 `YYYYMMDD`（K 线为交易日，财报为报告期 end_date） |
| `try_count` | Integer | 累计补拉尝试次数；DB 端原子自增 |
| `last_try_time` | DateTime | 最后一次尝试时间 |

**唯一键：** `(ts_code, missing_entity, missing_date)` —— upsert 冲突键。

**索引：** 单列索引齐全（ts_code / missing_entity / missing_date / try_count / last_try_time），方便按任一维度查询。

### 2.2 missing_entity 取值

| 值 | 含义 | 写入方 |
|----|------|--------|
| `financial_report_income` | 利润表缺期 | `ReportWorkflow` |
| `financial_report_balance` | 资产负债表缺期 | `ReportWorkflow` |
| `financial_report_cashflow` | 现金流量表缺期 | `ReportWorkflow` |
| `kline_daily` | 日线缺日 | `KlineWorkflow` |
| `kline_adj_factor` | 复权因子缺日 | `KlineWorkflow` |
| `kline_stk_limit` | 涨跌停缺日 | `KlineWorkflow` |

> 新增缺失实体类型时，**先在本表 §2.2 登记**再写代码，命名沿用 `<域>_<细分>` 蛇形小写。

---

## 3. 数据访问 API

类：[`MissingLog`](../../src/etl/log/missing_log.py)（无状态，每次实例化新建 `Database()` 持有 session）。

### 3.1 `upsert_missing_logs(missing_items, missing_entity) -> int`

**用途：** 登记一批缺失项；已存在则 try_count + 1、刷新 last_try_time。

**入参：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `missing_items` | `list[str]` | 元素格式 `"<ts_code>,<missing_date>"`，调用方负责拼接 |
| `missing_entity` | `str` | §2.2 中的取值；默认 `"report"` 是历史遗留，**调用方必须显式传**，详见 §6 |

**返回：** 处理的记录数（含已存在的更新；去重后入库的条数）。空入参或全为非法值时返回 `0`。

**SQL：** 单次 `INSERT ... ON CONFLICT (ts_code, missing_entity, missing_date) DO UPDATE`，`try_count = try_count + 1`，`last_try_time` 取 `excluded`。

**幂等性：** 是。同一批反复写不会改变最终行数，只会让 try_count 累计。

**调用方约定：** 入参 `missing_items` 内部去重（同 (ts_code, missing_date) 只保留首次出现）；`ts_code`/`missing_date` 两侧 `strip()`；空字符串行被静默丢弃。

### 3.2 `delete_missing_logs(missing_items, missing_entity) -> int` 【**新契约，待实现**】

**用途：** 补拉成功后，从 `log_missing` 物理删除对应行。

**入参：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `missing_items` | `list[str]` | 与 §3.1 同格式 `"<ts_code>,<missing_date>"` |
| `missing_entity` | `str` | §2.2 中的取值；必传 |

**返回：** 实际删除行数（不存在的项静默跳过）。

**SQL：** 单次 `DELETE ... WHERE missing_entity = :e AND (ts_code, missing_date) IN (...)`，使用 PG tuple-IN 一次删完，避免 N+1。

**幂等性：** 是。重复删不报错，第二次 `affected_rows=0`。

**实现备注：** 现有 `def delete_missing_logs(self, ts_code, missing_entity, missing_date)` 是单条空实现且 docstring 与方法名矛盾，需按本节签名重写。

### 3.3 `get_missing_log(ts_code, missing_entity, missing_date) -> LogMissing | None`

**用途：** 单条查询。已实现。返回 ORM 对象或 `None`。

### 3.4 `get_missing_log_by_ts_code(ts_code, missing_entity=None) -> list[LogMissing]` 【**新契约，待实现**】

**用途：** 按股票查询其所有「仍未补入库」的缺失项。

**入参：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `ts_code` | `str` | 股票代码 |
| `missing_entity` | `str \| None` | 可选过滤；`None` 时返回该股全部域的缺失项 |

**返回：** `list[LogMissing]`，按 `missing_date` 升序。空集合返回 `[]`。

**用例：**
- 补拉前批量预热：单股触发补拉时先查本表拿到全部待办，避免重复发现。
- Admin 页面展示「某股遗留缺失」清单。
- 串行重试器（未实现）扫表选取候选。

---

## 4. 调用方接入规约

所有缺失项登记/解除登记，**必须**走 `MissingLog`，不得在调用方手写 SQL 操作 `log_missing` 表。

### 4.1 标准三步式

```
完整性校验 → 拿到 missing_dates / missing_periods
   ↓
[初始登记] upsert_missing_logs(items, missing_entity)            # try_count++ / 刷新 last_try_time
   ↓
[逐项/批量补拉]  Extract → Transform → Load
   ↓
[终态分流]
   ├─ saved > 0 的项：delete_missing_logs(succeeded, missing_entity)   # ★ 替代旧的 upsert(...,=1)
   └─ saved = 0 的项：upsert_missing_logs(failed, missing_entity)      # 再写一次让 try_count++
```

### 4.2 `missing_items` 格式

固定 `f"{ts_code},{missing_date}"`，缺一不可。`missing_date`：

- **K 线域：** 交易日 `YYYYMMDD`（如 `20250115`）
- **财报域：** 报告期 end_date `YYYYMMDD`（季末，如 `20250331`）

### 4.3 批量边界

- Workflow 层应**按股聚合**后调用，每股单次补拉链路最多 2 次 upsert + 1 次 delete（成功批 / 失败批分两批），而**不是**逐条调用。
- 已正确实现批量化的位置：[`report_workflow._handle_missing_periods`](../../src/etl/workflow/financial/report_workflow.py)、[`kline_workflow.check_kline_complete_by_ts_code`](../../src/etl/workflow/kline/kline_workflow.py)。

---

## 5. 迁移历史

> 已完成。保留供后续审计；当前代码与本 spec 一致。

| 迁移项 | 原状态 | 当前状态 |
|--------|--------|----------|
| 成功项处理 | `upsert_missing_logs(..., last_try_result=1)` 保留行 | `delete_missing_logs(items, missing_entity)` 物理删除 |
| `delete_missing_logs` | 空函数 + docstring 与方法名矛盾 | 按 §3.2 实现 |
| `get_missing_log_by_ts_code` | `pass` | 按 §3.4 实现 |
| `last_try_result` 字段 | 表中存在但语义恒为 0 | 列与索引 `idx_log_missing_last_try_result` 已 DROP |
| `upsert_missing_logs.missing_entity` 默认值 | 默认 `"report"`（误导） | 保留默认值不动以减小改动；调用方均显式传值 |
| `report_workflow._handle_missing_periods` | 成功批走 upsert(=1) | 已改为 `delete_missing_logs(succeeded, spec.missing_entity)` |
| `kline_workflow._check_complete_by_ts_code` | 同上 | 同上 |
| 历史 `last_try_result=1` 行 | 184 万行积压（kline_stk_limit 域） | 已一次性 `DELETE WHERE last_try_result=1` 清空，随后 `VACUUM ANALYZE` |

---

## 6. 业务规则

### 6.1 唯一键与冲突

- 冲突键 `(ts_code, missing_entity, missing_date)`，三者全不为 NULL/空字符串。
- PG 视 NULL ≠ NULL，**任一字段为 NULL 都会破坏 upsert**；当前实现对 `ts_code`/`missing_date` 已 `strip()` + 空值过滤；`missing_entity` 由调用方显式传非空字符串保证。

### 6.2 try_count 自增

由 DB 端 `try_count = try_count + 1` 保证原子；并发场景安全。**初始登记** 与 **失败重登** 共用同一 upsert，因此「初次发现」会写入 `try_count=1`、「再次失败」会变成 `2, 3, ...`。

### 6.3 不在本模块的责任

- 限流：补拉调外部 API 的限流由各域 Client 层负责。
- 重试调度：本模块只是登记表，**不触发**重试。重试当前由各 Workflow 在同一次 CLI 运行内逐项重试。跨次/定时重试（扫 `log_missing` → 自动补拉）尚未实现。

---

## 7. 日志与可观测性

| 机制 | 说明 |
|------|------|
| `tqdm` 进度条 | 由调用方（Workflow/Strategy）负责，本模块不打印 |
| 返回值 | upsert / delete 返回受影响行数；调用方目前丢弃 |
| 直接观测 | `SELECT missing_entity, COUNT(*), MAX(try_count) FROM log_missing GROUP BY missing_entity` 看各域积压 |

---

## 8. 已知限制与实现备注

| 项 | 说明 |
|----|------|
| 自动重试缺失 | 没有「定时扫 log_missing → 重补」的后台任务；当前依赖再次跑 CLI 触发完整性校验时重新发现并重试 |
| Admin 入口缺失 | Admin 没有展示 `log_missing` 的页面；Service/Router 未开发 |
| `try_count` 无上限 | 永久失败的项（如已退市股的历史缺期）会无限累计；需要外部清理策略 |

---

## 9. 相关 spec

| spec | 关系 |
|------|------|
| [财报-完整性校验.sdd.md](./财报-完整性校验.sdd.md) | 主要写入方 1：三表缺期登记/解除登记 |
| [K线-完整性校验.sdd.md](./K线-完整性校验.sdd.md) | 主要写入方 2：日线/复权/涨跌停缺日登记/解除登记 |
| [`spec/load/存储-先查再改再插.sdd.md`](../load/存储-先查再改再插.sdd.md) | 业务表入库模式；本 spec 与之解耦，本表只是登记不参与业务 upsert |
