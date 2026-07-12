---
name: vibe_tushare_etl
deprecated: use vibe_tushare_fullstack
description: |
  已 deprecated，请改用 vibe_tushare_fullstack。本 Skill 仅保留 ETL spec + 8 层骨架（Step 0-4 子集）。
---

# Tushare ETL 自动生成 Skill（legacy）

> **新任务请用** [`.claude/skills/vibe_tushare_fullstack/skill.md`](../vibe_tushare_fullstack/skill.md)。

## 工具路径

- Skill 目录：`.claude/skills/vibe_tushare_etl/`
- SDD 模板：`.claude/skills/vibe_tushare_etl/templates/sdd_template.md`
- 骨架生成器：`.claude/skills/vibe_tushare_etl/generate_skeleton.py`
- 依赖 skill：`get_tushare_doc`（获取 Tushare 接口文档）
- **命名规范**：[`docs/ETL模块分类与命名规范.md`](../../docs/ETL模块分类与命名规范.md)（域目录 + 域前缀文件名 + DB 表名映射）

## 域目录与命名规范

新增 ETL 必须遵循 `docs/ETL模块分类与命名规范.md` 的域目录 + 域前缀结构。

**域目录**（`financial` / `market` / `kline` / `stock` / `index` / `warehouse`）：每层 ETL 目录下的子目录，文件放在对应域目录内。

**域前缀**：文件名和 DB 表名必须带域前缀（如 `market_daily_basic` 不是 `daily_basic`）。

**映射规则：**
| Tushare API | 域目录 | 域前缀 | DB 表名 |
|---|---|---|---|
| `daily_basic` | `market/` | `market_daily_basic` | `market_daily_basic` |
| `dividend` | `market/` | `market_dividend` | `market_dividend` |
| `hsgt_top10` | `market/` | `market_northbound` | `market_northbound_top10` |
| `stk_factor_pro` | `kline/` | `kline_stock_factor` | `kline_stock_factor` |
| `income_vip` 等 | `financial/` | `financial_report` | `financial_report_income` 等 |
| `stk_holdernumber` | `financial/` | `financial_stock_holder` | `financial_stock_holder` |
| `suspend_d` | `stock/` | `stock_suspend` | `stock_suspend` |
| `trade_cal` | `stock/` | `stock_trade_calendar` | `stock_trade_calendar` |

**完整映射表见** [`docs/ETL模块分类与命名规范.md`](../../docs/ETL模块分类与命名规范.md)。

**Step 2 新增问题：** 确认数据源属于哪个域目录（`financial` / `market` / `kline` / `stock` / `index` / `warehouse`），以及对应的域前缀。

**文件路径示例（以 `market_northbound` 为例）：**
```
src/etl/strategy/market/market_northbound_strategy.py
src/etl/workflow/market/market_northbound_workflow.py
src/etl/load/market/market_northbound_load.py
src/etl/extract/market/market_northbound_extract.py
src/etl/extract/local/market/market_northbound_local_extract.py
src/etl/client/market/market_northbound_tushare_client.py
src/etl/client/market/market_northbound_common.py
src/entities/data_entities/market/market_northbound_top10_entities.py
src/model/market/market_northbound_model.py
src/service/market/market_northbound_service.py
```

DB 表名 = 域前缀 + 概念名（如 `market_northbound_top10`），在 entity 的 `__tablename__` 中定义。

## 工作流程

### Step 1: 获取 Tushare 接口文档

**用户给了 URL 或 doc_id：**
```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py fetch <url_or_doc_id> -o
```

**用户给了接口名：**
```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py search "<api_name>" -d
```

从返回的 Markdown 中提取：
- `api_name`：接口名（如 `top_inst`）
- `title`：文档标题（如 `龙虎榜机构交易单`）
- `input_params`：输入参数表（名称、类型、必选、描述）
- `output_params`：输出参数表（名称、类型、默认显示、描述）
- `rate_limit`：限流信息（如有）
- `usage_example`：调用示例代码
- `data_example`：数据示例

### Step 2: 交互确认关键决策

用 AskUserQuestion 依次确认以下决策（可合并为 1-2 个问题）：

**问题 1：数据分类**
选项：基础数据 / 行情数据 / 财务数据 / 参考数据 / 特色数据 / 两融及转融通 / 资金流向 / 打板专题 / ETF / 指数 / 公募基金 / 期货 / 现货 / 期权 / 债券 / 外汇 / 港股 / 美股 / 宏观经济

**问题 2：拉取模式**
选项：
- **按日期遍历**（如 suspend_d、daily）— 逐交易日拉全市场
- **按期次遍历**（如 income_vip、balancesheet_vip）— 逐报告期拉全市场
- **全量快照**（如 stock_basic）— 一次拉全量
- **按个股拉取**（如 income 非 VIP）— 逐股拉历史

**问题 3：冲突键**
根据输出参数推荐默认值，让用户确认：
- 推荐逻辑：`ts_code` + 时间字段（`trade_date` / `end_date`）+ 其他维度字段
- 用户可自定义

**问题 4：是否需要 Transform 层**
选项：
- **简单入库**（无 Transform，如 stock_list、suspend_d）
- **去重 + JSONB**（如财报三表：merge_now + 非核心字段转 JSONB）
- **自定义**（用户描述清洗规则）

**问题 5：是否需要完整性校验**
选项：
- **需要**（宏观快照 + 微观查漏，如 K 线、财报）
- **不需要**（简单数据，如股票列表、停复牌）

**问题 6：CLI 命令名**
推荐默认值（基于分类和接口名），让用户确认：
- 子命令组名：`<domain>`（如 `dragon_tiger`）
- 命令名：`pull-<mode>`（如 `pull-by-date`、`pull-by-period`、`pull-all`）

### Step 3: 生成 SDD spec

1. 读取模板：`.claude/skills/vibe_tushare_etl/templates/sdd_template.md`
2. 用 Step 1 的文档信息 + Step 2 的决策填充所有占位符
3. 写入 `spec/etl/<分类>-<功能名>.sdd.md`
4. 展示给用户确认

**填充规则：**
- `{{api_name}}` → 接口名
- `{{title}}` → 文档标题
- `{{domain}}` → 数据分类对应的 domain 名
- `{{domain_dir}}` → 域目录名（`financial` / `market` / `kline` / `stock` / `index` / `warehouse`）
- `{{table_name}}` → 目标表名（默认 = api_name 或用户指定）
- `{{cli_group}}` → CLI 子命令组名
- `{{cli_command}}` → CLI 命令名
- `{{pull_mode}}` → 拉取模式
- `{{conflict_keys}}` → 冲突键列表
- `{{input_params_table}}` → 输入参数 Markdown 表格
- `{{output_params_table}}` → 输出参数 Markdown 表格
- `{{rate_limit}}` → 限流值
- `{{usage_example}}` → 调用示例代码块
- `{{data_example}}` → 数据示例代码块
- `{{architecture_diagram}}` → 根据拉取模式选择对应的架构图
- `{{flowchart}}` → Mermaid 调用流程图
- `{{sequence_diagram}}` → Mermaid 时序图
- `{{step_table}}` → 逐步说明表格
- `{{business_rules}}` → 业务规则（根据决策生成）
- `{{known_limitations}}` → 已知限制

### Step 4: 生成代码骨架

运行骨架生成器：
```bash
uv run python .claude/skills/vibe_tushare_etl/generate_skeleton.py \
  --api-name <api_name> \
  --domain <domain_prefix> \
  --domain-dir <domain_dir> \
  --table-name <table_name> \
  --pull-mode <by-date|by-period|snapshot|by-code> \
  --conflict-keys "<key1,key2,...>" \
  --input-fields "<field1:type1,field2:type2,...>" \
  --output-fields "<field1:type1,field2:type2,...>" \
  --rate-limit <number> \
  --has-transform <true|false> \
  --has-completeness <true|false> \
  --cli-group <group> \
  --cli-command <command> \
  --spec-path <spec/etl/xxx.sdd.md>
```

参数说明：
- `--domain`：域前缀，如 `market_northbound`（不是旧的 `hsgt`）
- `--domain-dir`：域目录名，必须是 `financial` / `market` / `kline` / `stock` / `index` / `warehouse` 之一
- `--table-name`：DB 表名，必须带域前缀，如 `market_northbound_top10`（不是旧的 `hsgt_top10`）

生成器会：
1. 创建所有必要的目录
2. 生成每个层级的代码文件（含 TODO 标记和注释指引）
3. 输出文件清单和每个文件的 TODO 列表

**不自动修改已有文件**（如 cli.py、setting.py、tushare_entities.py），而是输出需要手动添加的代码片段。

### Step 5: 人工确认 + 开发

1. 展示生成的文件清单
2. 展示每个文件的 TODO 列表
3. 用户确认后，逐文件填充实现（或直接让用户手动开发）

## 回复规范

1. **Step 1 完成后**：展示提取到的 API 信息摘要（接口名、输入/输出参数数量、限流）
2. **Step 2 完成后**：汇总所有决策（分类、模式、冲突键等）
3. **Step 3 完成后**：展示生成的 spec 文件路径，提示用户 review
4. **Step 4 完成后**：展示文件清单 + TODO 列表
5. **全程**：不自动修改已有文件，只输出建议的修改内容
