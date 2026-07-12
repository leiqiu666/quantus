# bulk_upsert_postgresql 性能深度分析

> 实现位置：`src/common/database.py` → `Database.bulk_upsert_postgresql`  
> 典型案例：[财报-report_income入库load_report性能分析.md](./财报-report_income入库load_report性能分析.md)

---

## 一、当前流程概览

1. 校验 `conflict_keys` 与唯一约束（inspector 查表元数据）
2. 构建 `INSERT ... ON CONFLICT DO UPDATE` 语句
3. `_check_field_lengths` 全量检查每条记录的字段长度（可通过 `skip_length_check=True` 跳过）
4. 构建 `values` 列表（每条 record 转成与表列对齐的 dict）
5. `session.execute(upsert_stmt, values)` 执行
6. `session.commit()`

---

## 二、性能瓶颈与优化空间

### 1. 网络 / 执行方式

**现状**：`session.execute(upsert_stmt, values)` 传入 list of dict 时，底层多为 `cursor.executemany(statement, values)`。  
**psycopg2 行为**：部分版本/配置下 `executemany` 对参数列表逐条执行，即 **N 条 = N 次 round-trip**，延迟和网络开销随 N 线性增长。

**适用场景**：应用与 PostgreSQL **跨机部署**、延迟 >1ms 时，此项往往是 P0。

**优化**：

- 连接串使用 `postgresql+psycopg2://...` 以明确驱动；若用 `psycopg`（v3），查阅其批量执行最佳实践。
- SQLAlchemy 2 部分版本支持 `executemany_mode`（需与驱动版本匹配；当前项目 psycopg2 环境实测 `batch` 模式不可用）。

**注意**：**localhost + 索引很多的表**（如 `report_income` 13 个索引）时，瓶颈常在 **索引写放大** 而非 round-trip，见 [财报入库案例分析](./财报-report_income入库load_report性能分析.md)。

---

### 2. 索引写放大（宽表 / 多索引场景）

**现状**：每次 `ON CONFLICT DO UPDATE` 对非 conflict 列全部 `SET col = excluded.col`；表上索引越多，单行写入成本越高。

**实测参考**（`report_income`，5645 行，13 索引，localhost）：

- 单行约 **~2ms**
- 与表是否已有历史数据关系不大（空表首次 INSERT 同样 ~11s）

**优化**：

- 写入表只保留 **PK + upsert 唯一键** 等必要索引；分析用索引放到副本或物化视图。
- 历史全量：`COPY` + 事后建索引，或临时 drop 非关键索引再 rebuild。
- 进阶：仅更新变更列（应用层 diff 后生成 partial `SET`），实现成本较高。

---

### 3. 字段长度检查 O(records × columns)

**现状**：`_check_field_lengths` 对每条记录的每个字段做长度判断，并构建 violations 结构。

**优化**（**已实现**）：

- 参数 **`skip_length_check: bool = False`**。ETL 等上游已校验的数据可设为 `True`。
- 若保留检查，可发现第一条超长即报错，避免收集全部 violations。

---

### 4. values 列表构建

**现状**：对每条 record 遍历列名取值。

**优化**（**已实现**）：

- `valid_columns`、`pk_columns` 在方法开头预计算为 `tuple` / `frozenset`。

---

### 5. 单次事务与锁

**现状**：所有记录在一次 `execute` + 一次 `commit` 中完成。记录数极大（如 10 万+）时事务长、持锁久、WAL 压力大。

**优化**（**已实现**）：

- 参数 **`chunk_size: Optional[int] = None`**：按块多次 `execute`，最后统一 `commit`（或按块 commit，在吞吐与锁时长间权衡）。
- 小批量（如 5k 行）下 chunk 对总耗时改善可能不明显，视表索引与磁盘而定。

---

### 6. 唯一约束检查

**现状**：每次调用 `_has_unique_constraint` 都会 `inspect(engine)` 并查元数据。

**优化**：

- 对 `(table_name, conflict_keys)` 做进程内缓存（含 TTL 或迁移后失效）。

---

### 7. 连接与连接池

**现状**：`create_engine(database_url, echo=False)` 默认池配置。

**优化**：

- 高并发场景配置 **`pool_size` / `max_overflow`**（`.env` 中已有 `POSTGRESQL_POOL_SIZE` 等占位，需在 `Database` 初始化时接入）。

---

## 三、优化项优先级建议

| 优先级 | 项 | 预期收益 | 实现成本 | 状态 |
|--------|-----|----------|----------|------|
| P0 | 精简写入表索引 / COPY+建索引 | 高（多索引表） | 中 | 待业务评估 |
| P0' | 远程库 batch executemany | 高（round-trip） | 低 | 视部署 |
| P1 | `skip_length_check` | 低–中（CPU） | 低 | ✅ 已实现 |
| P2 | `chunk_size` 分批 | 中（锁/WAL/超大事务） | 低 | ✅ 已实现 |
| P3 | `valid_columns` 预计算 | 低 | 低 | ✅ 已实现 |
| P4 | 唯一约束检查缓存 | 低 | 中 | 待做 |

建议：

- **远程连库、索引少**：优先 P0' + P1。
- **localhost、索引多（财报三表）**：优先 P0 + P2/P3 边际优化。

---

## 四、与常见实践的对照

| 方案 | 说明 |
|------|------|
| `INSERT ... ON CONFLICT DO UPDATE` | 当前实现，语义正确；多索引时单行成本由索引数主导 |
| `COPY` | 纯插入最快；无冲突场景的 bulk load 首选 |
| 临时去索引再 rebuild | 历史全量初始化常用 |
| 只更新变更列 | 减少 JSONB / 宽列写放大，实现复杂 |

---

## 相关文档

- [财报-report_income入库load_report性能分析.md](./财报-report_income入库load_report性能分析.md) — 服务器 11s vs 本地 2s 案例
- `src/etl/load/financial/report_load.py` — 财报入库调用方
