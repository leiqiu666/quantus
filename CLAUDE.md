# Quantus · AI 协作规范

> 给 AI 编码助手（Claude Code / Cursor / Codex 等）的项目级 **协作灵魂文件**。
> **不重复**已经在 [`docs/开发进度.md`](docs/开发进度.md) 与各域 `spec/<域>/README.md` 里的内容，本文件只写「读代码也推不出来」的东西：指针、约定、踩过的坑、个人偏好。
> 子目录另有专属约定的，单独维护 sub-CLAUDE：当前仅 [`src/web/admin/CLAUDE.md`](src/web/admin/CLAUDE.md)。

### 文档分工（先看哪份）

| 文档 | 角色 | 何时改 |
|------|------|--------|
| **本文件 `CLAUDE.md`** | 跨模块约定、架构禁区、隐藏坑、风格偏好 | 踩坑 / 定新约定时 |
| [`docs/开发进度.md`](docs/开发进度.md) | 功能盘点：CLI 命令、API、Admin 页、源码路径 | **每增删功能必改** |
| `spec/<域>/*.sdd.md` | 单功能详细设计（输入/分层/SQL/边界） | 写功能前先起草或改 spec |
| [`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md) | 域目录 + 域前缀 + DB 表名映射 | 新增 ETL 数据源时 |
| [`docs/量化层完整方案.md`](docs/量化层完整方案.md) | 量化研究 Phase 路线图 | 因子 / 回测方向变更时 |
| [§3 AI Skills 应用指导](#3-ai-skills-应用指导) + [`.claude/skills/`](.claude/skills/) | 新增 ETL / Admin 页的可重复工作流 | 用 Skill 编排的任务；新增 Skill 时 |

---

## 1. 项目速览

单人开发的 A 股量化数据平台，四块在跑：

| 模块 | 入口 | 说明 |
|------|------|------|
| ETL CLI | `uv run ./src/etl/cli.py` | Typer 子命令 + 交互菜单（`_MENU_ROWS`），数据拉取 / 完整性校验 / PG→Parquet |
| Research CLI | `uv run ./src/research/cli.py` | 因子计算（Parquet）、PG 热层同步、Tushare 技术因子入库；spec 见 [`spec/quant/`](spec/quant/) |
| HTTP API | `quantus-api` / `uvicorn src.api.main:app` | FastAPI，端口 8000，`/docs` 看 OpenAPI |
| Admin | `src/web/admin`（`pnpm dev`） | React 19 + antd v6 + Vite 7；规范见 [`src/web/admin/CLAUDE.md`](src/web/admin/CLAUDE.md) |

技术栈：Python 3.13 + uv + SQLAlchemy + PostgreSQL + Polars + Pydantic Settings + Tushare + 通达信本地 HTTP；列存仓库 Parquet（`WAREHOUSE_ROOT`）+ DuckDB 验证。

**当前功能盘点**：[`docs/开发进度.md`](docs/开发进度.md)。任何新增/删除功能时，同步改这张表 + 对应 `spec/<域>/README.md` 索引。

---

## 2. 文档与 spec 体系

| 想找什么 | 看哪里 |
|----------|--------|
| 已有什么功能、对应文件、调什么 API | [`docs/开发进度.md`](docs/开发进度.md) |
| 某个 ETL 命令的详细设计（输入/分层/SQL/边界） | [`spec/etl/<功能>.sdd.md`](spec/etl/) |
| 因子 / 回测 / 量化研究 | [`spec/quant/<功能>.sdd.md`](spec/quant/) + [`docs/量化层完整方案.md`](docs/量化层完整方案.md) |
| 某个 API 的接口契约 | [`spec/api/<客户端>/<功能>.sdd.md`](spec/api/)（按 `admin` / `client` 分组） |
| 通用存储 / upsert 模式 | [`spec/load/存储-先查再改再插.sdd.md`](spec/load/存储-先查再改再插.sdd.md) |
| ETL 域目录与表名命名 | [`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md) |
| 环境变量清单 | [`src/common/setting.py`](src/common/setting.py) + 各 spec 的「前置依赖」节 |

**SDD 优先**：写新功能前先起草 / 改 `spec/<域>/<功能>.sdd.md`，对齐方案再动代码。已有 spec 改动也要先 review。

---

## 3. AI Skills 应用指导

项目级 Skills 在 [`.claude/skills/`](.claude/skills/)，是**可重复的工作流剧本**（含脚本路径、交互步骤、产出物）。Skill 不替代本文件的架构约定，而是在特定任务里**编排** spec → 代码 → 文档更新。

### 3.1 怎么触发

| 工具 | 做法 |
|------|------|
| **Cursor** | 对话里描述意图（见下表「典型说法」）；或 `@.claude/skills/<name>/skill.md` 显式引用 |
| **Claude Code** | Slash 命令，如 `/get_tushare_doc search daily` |

**AI 执行任何 Skill 前，必须先 Read 对应 `skill.md` 全文**，按其中的 Step 顺序走，不要凭记忆跳步。

### 3.2 选用规则（什么时候用哪个）

| 用户意图 / 场景 | 用哪个 Skill | 典型说法 |
|-----------------|-------------|----------|
| 查 Tushare 接口字段、限流、示例 | [`get_tushare_doc`](.claude/skills/get_tushare_doc/skill.md) | 「查一下 tushare 的 daily 接口」「这个 doc_id=162 是什么接口」 |
| **新增 Tushare 数据源全链路**（ETL + CLI + 完整性 + Admin 看板 + SSE） | [`vibe_tushare_fullstack`](.claude/skills/vibe_tushare_fullstack/skill.md) | 「接入 top_inst 挂市场类看板」「Tushare 链接全链路开发」 |
| 独立 ProTable 明细页 / 非看板 Admin CRUD | [`admin_web_dev`](.claude/skills/admin_web_dev/skill.md) | 「龙虎榜机构逐条明细页」「调度页加字段」 |
| 改已有 ETL 逻辑、修 bug、小改字段 | **不用 Skill**，直接读 `spec/etl/*.sdd.md` + 源码 | — |
| 新增自研因子、回测 | **暂无 Skill**，读 [`spec/quant/`](spec/quant/) + [`docs/量化层完整方案.md`](docs/量化层完整方案.md) | — |

**已 deprecated（仍可读，新任务勿用）**：[`vibe_tushare_etl`](.claude/skills/vibe_tushare_etl/skill.md)（仅 ETL 骨架）。

**依赖关系**：`vibe_tushare_fullstack` Step 0 调用 `get_tushare_doc`；单独查文档时只用后者。

### 3.3 Skill 速览

| Skill | 主脚本 / 模板 | 产出物 |
|-------|--------------|--------|
| `get_tushare_doc` | `.claude/skills/get_tushare_doc/tushare_doc.py` | 本地 `doc/*.md` + 终端 Markdown |
| `vibe_tushare_fullstack` | `generate_skeleton.py` + `templates/` + `mappings/dashboard_groups.yaml` | `spec/etl/*.sdd.md` + 8 层骨架 + 看板列/SSE 片段 + checklists |
| `admin_web_dev` | 纯流程（模式 B） | 独立 ProTable 页 + Router/Service；**不含**看板列 |
| `vibe_tushare_etl` | legacy | 同 fullstack 的 ETL 子集，已 deprecated |

### 3.4 执行原则（所有 Skill 通用）

1. **SDD 先于代码**：`vibe_tushare_fullstack` Step 2 生成 spec 并经用户确认后，才 Step 3+ 动代码；`admin_web_dev` 有现成 spec 则先读 [`spec/api/admin/`](spec/api/admin/)。
2. **命名走域规范**：新 ETL 的域目录、域前缀、DB 表名以 [`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md) 为准；**大类**以 [`vibe_tushare_fullstack/mappings/dashboard_groups.yaml`](.claude/skills/vibe_tushare_fullstack/mappings/dashboard_groups.yaml) 为准。
3. **骨架 ≠ 完工**：`generate_skeleton.py` 只出 TODO 占位；CLI、env、看板列、SSE 注册等按 checklist 手动或后续对话补齐。
4. **收尾必做**：功能落地后更新 [`docs/开发进度.md`](docs/开发进度.md) + 对应 `spec/<域>/README.md` 索引。
5. **自验**：ETL 跑 CLI；Admin 看板点通 SSE 补位；涉及 upsert 手动看 DB。

### 3.5 `vibe_tushare_fullstack` 流程摘要

```
get_tushare_doc（Step 0）
  → Step 1 确认 Admin 大类 group_id + 拉取模式 / 冲突键 / 完整性
  → Step 2 spec/etl/*.sdd.md（含 Admin/SSE 节）
  → Step 3 generate_skeleton → 8 层 + 看板/SSE 片段
  → Step 4–5 ETL + CLI + check_complete
  → Step 6 completeness_dashboard_config + etl_sse_registry（默认不改 routes）
  → Step 7 调度可选 → Step 8 自验 + 开发进度
```

拉取模式：`by-date` → SSE 开市日；`by-period` → 报告期；`snapshot` → 全量；`by-code` → 逐股。细节见 fullstack skill。

### 3.6 `admin_web_dev` 流程摘要（模式 B）

```
确认：独立明细 ProTable / 非看板 CRUD
  → 后端 schemas → service（src/service/）→ router
  → 前端 types → services → pages → routes.config.tsx
  → spec/api/admin/*.sdd.md → 更新开发进度
```

量化数据源看板列 → 用 `vibe_tushare_fullstack` Step 6，**不要**按本流程新建宽表页。

---

## 4. ETL 分层约定（重要）

固定四层，**不要**在层之间打洞或合并：

```
CLI (typer) → Strategy (区间/全市场编排) → Workflow (单股/单日 ETL 串联)
                                            → Extract → Transform → Load
```

- **CLI**：仅参数解析 + 调 Strategy；只在子命令路径 `typer.echo`，交互菜单路径不 echo。
- **Strategy**：负责区间循环、`ensure_trade_cal`、批量预加载（resolved / suspend）、tqdm 进度条；不直接调 Extract/Load。
- **Workflow**：单股或单日的 Extract→Transform→Load 串联；接收 Strategy 注入的预加载数据，**不**逐股查 DB。
- **Extract / Transform / Load**：纯粹的拉/转/写；Extract 内部可做数据源链降级（如 `tdx_quant → tushare`）。

**K 线三维度（daily / adj_factor / stk_limit）** 用 spec dispatch 共享同一套 Workflow/Strategy，参数化在 `_KlineWorkflowSpec` / `_KlineStrategySpec`，详见 [`spec/etl/K线-完整性校验.sdd.md`](spec/etl/K线-完整性校验.sdd.md)。

**财报三表** 顺序固定：`income → balance → cashflow`。

**域目录 + 域前缀**（2026-06 重构后）：`strategy/`、`workflow/`、`load/` 等层下按 `financial/`、`market/`、`kline/`、`stock/`、`index/`、`warehouse/` 分子目录；文件名带域前缀（如 `market_daily_basic_strategy.py`），DB 表名同理（如 `market_daily_basic`）。完整映射见 [`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md)。

**Typer 组名 ≠ 域前缀**：CLI 交互菜单里的组名可能仍是历史短名（如菜单写 `dividend`），实际 Typer 注册可能是 `market_dividend` / `market_moneyflow` / `financial_forecast` / `financial_express`——以 [`src/etl/cli.py`](src/etl/cli.py) 的 `add_typer(..., name=...)` 为准。

---

## 5. API 层模式

新增 HTTP 端点前先看 [`spec/api/API开发规范.sdd.md`](spec/api/API开发规范.sdd.md)。两种主流模式：

| 模式 | 何时用 | 路由签名 | 调用 |
|------|--------|----------|------|
| ① Service 读 | 只读、秒级返回 | `def`（同步，跑线程池） | `src/service/<域>/*_service.py` → Model → PG |
| ② ETL Strategy + SSE 写 | 写库、调外部 API、分钟/小时级 | `async def`，返回 `StreamingResponse` | `sse_streaming_response(Strategy.method, ...)`，复用 CLI 用的 Strategy 方法 |

**别混的几个点：**

- `src/service/*`（领域 Service，ETL/CLI/API 共享）≠ `src/api/services/*`（router 私有胶水层，目前只有 `tdx_quant_service` 这种代理类）。普通业务读放前者。
- 同步 router 里**不要**直接调 ETL 写库方法 —— 占线程池、前端没进度。该上 SSE 就上 SSE。
- SSE worker **不要**自己 `await asyncio.to_thread(q.get)` —— 断连后占线程池，详见 [`src/common/sse.py`](src/common/sse.py) 顶部注释。
- Strategy 方法的 `progress_queue` 参数 CLI 不传时所有 put 跳过；同一份方法 CLI / API 复用，不要为 API 重写。

---

## 6. 容易踩的坑

| 主题 | 注意点 |
|------|--------|
| ON CONFLICT 与 NULL | PG 视 NULL ≠ NULL，凡进入冲突键的列必须在 finalize 时把 None/NaN 归一化为 `""` 或固定值（参考 `finalize_suspend` 对 `suspend_timing` 的处理），否则 upsert 失效、每次跑都重复 INSERT。 |
| stk_limit 列在哪里 | `up_limit` / `down_limit` 已经融合进 `kline_daily`，**没有**独立 `kline_stk_limit` 表；完整性判定时按这两列是否非空算 resolved。 |
| 全天停牌定义 | `suspend_d` 中 `suspend_type='S' AND suspend_timing=''`（空字符串，不是 NULL）。K 线完整性校验从「应有交易日」里扣除这一集合，**前提**是 `suspend pull-by-date` 已覆盖检查区间。 |
| 个股交易日历公式 | `SSE 开市日 ∩ [list_date, delist_date) − 全天停牌日`；只读路径用 [`StockTradeCalendarService.compute_stock_trade_calendar`](src/service/stock/stock_trade_calendar_service.py)，批量补拉路径用 Strategy 一次性预加载注入 Workflow。 |
| 上市存续区间 | 左闭右开 `[list_date, delist_date)`；`delist_date` 当日不算交易日。 |
| 95% 完整性阈值 | 宏观快照与 `pull-*-by-date-range` 跳过逻辑都按全市场 ≥95% 视为「该日完整」；跨任务保持一致。**财报分母排除 B 股**（9009xx.SH / 200xxx.SZ），**分子分母都剔除已退市股**（delist_date 非空）；K 线分母排除已退市股。 |
| 财报报告期生成 | 2005 年前只生成半年报（0630）和年报（1231），2005 年起四季报；起点默认 19900101。证监会 2005 年才强制要求季报。 |
| Tushare 限流 | K 线类接口 500/min，停牌/日历 200/min；用 [`common/function.py`](src/common/function.py) 的 `create_rate_limiter` 包装。 |
| `verify_api_token` 是占位 | [`src/api/deps.py`](src/api/deps.py) 目前**不真正校验**，新接口先按真鉴权写 deps，不要默认信任。 |
| TDX_QUANT_ENABLED=false | 通达信代理接口返回 503；本地无客户端时正常，CI/远端务必关掉。 |
| ETL 增量起点 | `ETL_DEFAULT_START_DATE` 全局兜底；各表 `{DB表名}_START_DATE` 覆盖（映射后表名，见 [`docs/ETL模块分类与命名规范.md`](docs/ETL模块分类与命名规范.md)）；`settings.etl_start_date("market_daily_basic")`；旧 env 名仍兼容见 [`src/common/etl_start.py`](src/common/etl_start.py) |

---

## 7. 常用命令

```bash
# ETL（交互菜单）
uv run ./src/etl/cli.py
# ETL（具体命令）— 完整清单见 docs/开发进度.md
uv run ./src/etl/cli.py kline check-complete
uv run ./src/etl/cli.py report check-report-complete
uv run ./src/etl/cli.py suspend pull-by-date --start-date 20250101

# Research（因子）
uv run ./src/research/cli.py
uv run ./src/research/cli.py factor update-all
uv run ./src/research/cli.py tushare-factor pull-by-date-range

# 开发态一键启动（API :8000 + Admin :5173；调度默认随 API 内嵌）
uv run ./start.py
uv run ./start.py --only api                   # 或 --only admin
uv run ./start.py --standalone-scheduler       # API 关内嵌 + 独立 quantus-scheduler
uv run ./start.py --list

# API / Admin 单独起
quantus-api                                    # = uvicorn src.api.main:app（见 pyproject scripts）
uvicorn src.api.main:app --reload --port 8000  # 开发热重载
cd src/web/admin && pnpm dev                   # http://localhost:5173

# 同步单表结构（每个 *_entities.py 末尾都有 if __name__ == "__main__"）
uv run ./src/entities/data_entities/<xxx>_entities.py
```

> 没有 `pytest` 套件、没有 lint 配置；目前**靠跑 CLI / 看 DB / 看 Admin** 自验。改动若涉及 SQL 或 upsert 行为，至少手动跑一次对应 CLI 命令。

---

## 8. 命名 / 风格偏好

- **命名**：CLI 子命令优先 `pull-by-date` / `pull-by-ts-code` / `check-complete`，不用 `history` 这种含糊词；K 线和停牌混用 `*_by_date_range` / `*_by_date`，保留历史差异不强行统一。
- **注释**：默认不写。只在「为什么」非显然时写一行——比如 `suspend_timing` 为何要归一化为空字符串这种隐藏约束。`# 用 X 做 Y` 这种废话不要。
- **新增功能**：先 `spec/<域>/<功能>.sdd.md` → review → 动代码 → 更新 [`docs/开发进度.md`](docs/开发进度.md) 与对应 `spec/<域>/README.md` 索引。
- **沟通语言**：中文回复；输出 terse，不复述已知信息，不在末尾加总结段。
- **不要**为了「向后兼容」保留 `_` 前缀的占位 / 重新导出 / `# removed` 注释；该删就删干净。
- **风险操作前确认**：destructive git 操作、删表、跑覆盖全市场的 `pull-*-by-date-range` 之前先问一句。

---

## 9. 已知缺口（提醒你不要假设它们存在）

- `verify_api_token` 是占位，没有真正的用户/权限体系
- 绝大多数 ETL / Research 写库命令**没有** HTTP/Admin 入口（财报三表+指标 SSE 入库除外），只能 CLI 触发
- Admin 已有因子列表只读页；仍缺基础数据维护页（停复牌 / 交易日历 / 股票列表）、K 线单股详情、Agent 管理页
- 量化层 Phase 2+（截面回测 / 多因子合成 / 事件驱动）仅有方案，代码未启动
- `src/collect/` 是被 ETL 取代的早期脚本骨架，可清理
- `src/agent/demo/` 是占位，没有业务逻辑
- 监控 / 告警 / 测试套件未启动
