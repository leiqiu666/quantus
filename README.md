# Quantus

A 股量化数据平台：ETL 入库 → Parquet 研究仓库 → 因子 / 截面回测 → Admin 运营与调度。

单人、**纯 Web Coding（AI 辅助）**建设；功能契约写在 Spec，可重复流程沉淀为 Skill。

---

## 1. 主要功能与系统架构

### 1.1 总体架构

```
外部数据源（Tushare / 通达信 tdx_quant）
        │
        ▼
┌─────────────────── ETL ───────────────────┐
│  CLI → Strategy → Workflow                 │
│       → Extract → Transform → Load         │
└───────────┬───────────────────┬────────────┘
            │                   │
            ▼                   ▼
     PostgreSQL（热/运营）   Parquet 仓库（研究权威）
            │                   │
            │                   ▼
            │            Research（因子 / 回测）
            │                   │
            └─────────┬─────────┘
                      ▼
         FastAPI + 内嵌调度 ←→ Admin（React）
```

| 层 | 职责 | 入口 |
|----|------|------|
| **ETL** | 拉数、完整性校验、PG↔Parquet | `uv run ./src/etl/cli.py` |
| **Research** | 因子计算、热层同步、截面回测 | `uv run ./src/research/cli.py` |
| **HTTP API** | 只读查询、SSE 写库、调度管理 | `quantus-api` / 端口 `8000` |
| **Admin** | 数据源看板、因子、调度等运营页 | `src/web/admin`（`pnpm dev`） |
| **Scheduler** | 定时跑 ETL（默认随 API 内嵌） | `SCHEDULER_ENABLED` |

技术栈：Python 3.13 · uv · SQLAlchemy · PostgreSQL · Polars · Parquet / DuckDB · FastAPI · React 19 · antd v6 · Vite 7。

功能盘点（命令 / API / 页面对照）：[`docs/开发进度.md`](docs/开发进度.md)。

---

### 1.2 ETL（数据管道）

固定四层，禁止跨层打洞：

```
CLI (Typer) → Strategy（区间 / 全市场编排）
            → Workflow（单股 / 单日串联）
            → Extract → Transform → Load
```

| 能力域 | 内容概要 |
|--------|----------|
| 基础 | 股票列表、交易日历、停复牌、活跃股数 |
| K 线 | 日线 / 复权 / 涨跌停三维度；95% 完整性 + 宏观快照 / 微观补位 |
| 财报 | income → balance → cashflow → indicator；按报告期 VIP 批量 |
| 市场 / 财务截面 | 估值、资金流、两融、北向、龙虎榜、分红、股东、预告快报等 |
| 指数 | 成分权重、日线、分类 / 成分快照 |
| 仓库 | PG `kline_daily` → 按月 Parquet；行数对账 |

域目录与表名前缀规范：[`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md)。  
ETL Spec 索引：[`spec/etl/`](spec/etl/)。

---

### 1.3 Research（因子与回测）

研究链路只认 **Parquet 冷层**；PG 因子表是热层 / 运营旁路，不替代仓库。

| 模块 | 说明 |
|------|------|
| **因子框架** | `BaseFactor` + `FactorRegistry`；自研因子写 `factor/{name}/dt=YYYYMM/` |
| **多源因子** | 自研计算、Tushare 93 因子、国泰 191（CLI + Admin SSE） |
| **FactorDataset** | 统一读取层，供回测消费 |
| **截面回测** | `backtest run`：单因子分组、IC / 净值 → `warehouse/backtest/` |
| **热层同步** | Parquet → PG `factor_latest` / `factor_meta`（Admin 列表） |

路线图与 Phase：[`docs/量化层完整方案.md`](docs/量化层完整方案.md)。  
Quant Spec：[`spec/quant/`](spec/quant/)。

---

### 1.4 API · Admin · 调度

| 模块 | 能力 |
|------|------|
| **API** | 健康检查、财报 SSE 入库、数据源看板 / 总览、ETL 补位 SSE、股票 / 因子列表、通达信代理、调度 CRUD |
| **Admin** | 量化数据源看板与总览、因子管理（含国泰 191 计算）、调度任务页 |
| **调度** | APScheduler 默认嵌在 API 进程；可选独立 `quantus-scheduler` |

API 规范：[`spec/api/API开发规范.sdd.md`](spec/api/API开发规范.sdd.md)。  
两种写读模式：**① Service 同步只读** · **② Strategy + SSE 长任务写库**。

---

### 1.5 存储分层

| 存储 | 用途 |
|------|------|
| **PostgreSQL** | 运营查询、完整性快照、因子热层、调度元数据 |
| **Parquet（`WAREHOUSE_ROOT`）** | K 线 / 因子 / 回测结果；研究与回测权威 |
| **DuckDB** | 校验与 ad-hoc 分析（不参与主写入路径） |

---

## 2. 建设规范与生产流程

### 2.1 建设方式：纯 Web Coding

本仓库以 **AI 编码助手（Cursor / Claude Code 等）+ 人审** 为主生产路径，而不是传统「先搭团队再手写脚手架」：

- 架构禁区、隐藏坑、偏好写在 [`CLAUDE.md`](CLAUDE.md)（AI 与人的共同契约）
- 功能「有没有、在哪」写在 [`docs/开发进度.md`](docs/开发进度.md)
- 单功能「怎么做」写在 `spec/<域>/*.sdd.md`
- 可重复的全链路任务沉淀为 [`.claude/skills/`](.claude/skills/) 剧本

目标：换一次对话 / 换一个助手，仍能按同一套规范落地，而不是靠个人记忆。

---

### 2.2 Spec（SDD）规范

**SDD 先于代码**：新功能先起草或改 `spec/<域>/<功能>.sdd.md`，对齐后再动实现。

| Spec 域 | 覆盖 |
|---------|------|
| [`spec/etl/`](spec/etl/) | 数据源拉取、完整性、冲突键、分层与边界 |
| [`spec/quant/`](spec/quant/) | 因子、回测、热层、Admin 因子相关 |
| [`spec/api/`](spec/api/) | HTTP 契约（按 `admin` / `client`） |
| [`spec/load/`](spec/load/) | 通用 upsert / 存储模式 |
| [`spec/scheduler/`](spec/scheduler/) | 调度系统设计 |

单份 Spec 通常包含：输入输出、分层职责、SQL / 表结构、边界与非目标、自验方式。  
落地后必须回写：`docs/开发进度.md` + 对应 `spec/<域>/README.md` 索引。

---

### 2.3 Skill 规范

Skill 是**可重复工作流**（步骤、脚本、模板、checklist），编排「查文档 → 写 Spec → 出骨架 → 接线 → 自验」，**不替代** `CLAUDE.md` 里的架构约定。

| Skill | 何时用 |
|-------|--------|
| [`get_tushare_doc`](.claude/skills/get_tushare_doc/skill.md) | 查 Tushare 字段 / 限流 / 示例 |
| [`vibe_tushare_fullstack`](.claude/skills/vibe_tushare_fullstack/skill.md) | **新增 Tushare 数据源全链路**（ETL + CLI + 完整性 + Admin 看板 + SSE） |
| [`admin_web_dev`](.claude/skills/admin_web_dev/skill.md) | 独立 ProTable / 非看板 CRUD 页 |

执行原则：

1. 先 Read 对应 `skill.md` 全文，按 Step 顺序走  
2. Spec 经确认后再写业务代码  
3. 命名服从 ETL 域规范与看板 `group_id` 映射  
4. 骨架脚本只出占位；收尾改开发进度并自验 CLI / Admin / DB  

小改、修 bug：**不用 Skill**，直接读已有 Spec + 源码。

---

### 2.4 生产流程（端到端）

以「接入一个新 Tushare 数据源」为主路径（其它功能可裁剪同构步骤）：

```
① 意图澄清（域 / 拉取模式 / 冲突键 / Admin 大类）
        │
        ▼
② get_tushare_doc —— 对齐官方字段与限流
        │
        ▼
③ 起草 spec/etl/*.sdd.md —— 人审通过
        │
        ▼
④ vibe_tushare_fullstack —— 骨架 + ETL/CLI/完整性/看板/SSE
        │
        ▼
⑤ 补齐实现与 checklist（env、注册、调度可选）
        │
        ▼
⑥ 自验：CLI 拉取 / check-complete → Admin 看板与 SSE → 抽查 DB upsert
        │
        ▼
⑦ 更新 docs/开发进度.md + spec 索引 → 提交
```

日常增量（改逻辑、修字段）可跳过 Skill，但仍建议：**改 Spec（若行为变）→ 改代码 → 更新开发进度 → 自验**。

文档分工速查：

| 文档 | 角色 |
|------|------|
| [`CLAUDE.md`](CLAUDE.md) | AI 协作约定、架构禁区、坑 |
| [`docs/开发进度.md`](docs/开发进度.md) | 功能清单（增删必改） |
| `spec/<域>/*.sdd.md` | 单功能详细设计 |
| [`.claude/skills/`](.claude/skills/) | 可重复生产剧本 |

---

## 3. 快速启动

```bash
# 开发态：API :8000 + Admin :5173（调度默认随 API）
uv run ./start.py

# 分模块
uv run ./src/etl/cli.py
uv run ./src/research/cli.py
cd src/web/admin && pnpm dev
```

- API 文档：http://localhost:8000/docs  
- Admin：http://localhost:5173  
- 无通达信时：`.env` 设 `TDX_QUANT_ENABLED=false`（非 Windows 默认即为 false）

环境变量以 [`src/common/setting.py`](src/common/setting.py) 与各 Spec「前置依赖」为准。
