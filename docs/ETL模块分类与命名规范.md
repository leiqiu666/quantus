# ETL 模块分类与命名规范

> 数据源 → 域前缀 → 文件名的映射关系。新增 / 改动 ETL 时以此为准。
> Tushare 接口缩写记录在各文件头部注释里，模块名用规范英文。
>
> 最后更新：2026-06-24（完成实际代码重构）

---

## 设计原则

**域目录 + 域前缀文件名**：每层目录（`strategy/`、`workflow/` 等）下按域建子目录（`financial/`、`market/`、`kline/`、`stock/`、`index/`、`warehouse/`），文件用 `{域}_{概念}_{层后缀}.py` 命名放在对应域目录下。

理由：
- 域目录提供物理分组，IDE 折叠/展开一目了然
- 文件名自带域前缀，grep / 全局搜索不受目录结构影响
- import 路径清晰：`from src.etl.strategy.market.market_northbound_strategy`
- 新增数据源只需在对应域目录下加文件

---

## 目录结构概览

```
src/etl/
├── client/                    # 远程 API 调用（Tushare / tdx_quant）
│   ├── base.py
│   ├── financial/
│   │   ├── financial_report_tushare_client.py
│   │   ├── financial_forecast_tushare_client.py
│   │   └── ...
│   ├── market/
│   │   ├── market_daily_basic_tushare_client.py
│   │   └── ...
│   ├── kline/
│   │   ├── kline_tushare_client.py
│   │   ├── kline_protocol.py
│   │   └── ...
│   ├── stock/
│   ├── index/
│   └── warehouse/
├── extract/                   # 数据源适配（远程 + 本地 DB 查询）
│   ├── base_extract.py
│   ├── financial/
│   │   ├── financial_report_extract.py
│   │   └── ...
│   ├── market/
│   ├── kline/
│   ├── stock/
│   ├── index/
│   ├── warehouse/
│   └── local/                 # 本地 DB 查询
│       ├── financial/
│       ├── market/
│       ├── kline/
│       ├── stock/
│       └── index/
├── load/                      # DB 入库
│   ├── financial/
│   ├── market/
│   ├── kline/
│   ├── stock/
│   ├── index/
│   └── warehouse/
├── workflow/                  # 单次 ETL 串联（Extract → Transform → Load）
│   ├── financial/
│   ├── market/
│   ├── kline/
│   ├── stock/
│   ├── index/
│   └── warehouse/
├── strategy/                  # 编排层（区间循环 / 增量起点 / 宏观快照）
│   ├── financial/
│   ├── market/
│   ├── kline/
│   ├── stock/
│   ├── index/
│   └── warehouse/
├── transform/                 # 数据转换
│   ├── financial/
│   ├── kline/
│   ├── stock/
│   └── warehouse/
└── log/
    └── missing_log.py

src/
├── entities/data_entities/    # SQLAlchemy 实体（按域分目录）
│   ├── financial/
│   │   ├── financial_report_income_entities.py
│   │   ├── financial_report_balance_entities.py
│   │   └── ...
│   ├── market/
│   ├── kline/
│   ├── stock/
│   ├── index/
│   ├── completeness_snapshot_entities.py  # 通用实体留在顶层
│   └── ...
├── model/                     # DB 查询封装（按域分目录）
│   ├── financial/
│   ├── kline/
│   └── stock/
├── service/                   # 业务 Service（按域分目录）
│   ├── financial/
│   ├── kline/
│   ├── stock/
│   └── etl/                   # ETL 通用配置
└── api/routers/               # HTTP 路由
```

---

## 域前缀定义

| 域前缀 | 含义 | 数据源数 |
|--------|------|---------|
| `financial_` | 财务：三表 / 指标 / 预告 / 快报 / 审计 / 股东 | 6 |
| `market_` | 市场指标：估值 / 分红 / 资金流 / 两融 / 北向 / 龙虎榜 / 大宗 | 7 |
| `kline_` | 行情：日线 / 复权 / 涨跌停 / 技术因子 / 内部因子管线 | 3 |
| `stock_` | 股票基础：列表 / 停复牌 / 交易日历 | 3 |
| `index_` | 指数：成分和权重 | 1 |
| `warehouse_` | 仓库：PG → Parquet 导出（独立） | 1 |

---

## 数据源完整映射表

### 1. `financial_`（财务域）— 6 个数据源

| Tushare API | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|------------|------|------|---------|----------------|---------|
| `income_vip` `balancesheet_vip` `cashflow_vip` `fina_indicator_vip` | 三表 + 财务指标 | `financial_report` | `financial_report_income` `financial_report_balance` `financial_report_cashflow` `financial_report_indicator` | `financial_report_strategy.py` | `financial/report` |
| `forecast_vip` | 业绩预告（预告类型 / 净利润区间） | `financial_forecast` | `financial_forecast` | `financial_forecast_strategy.py` | `forecast` |
| `express_vip` | 业绩快报（营收 / 利润 / 同比） | `financial_express` | `financial_express` | `financial_express_strategy.py` | `express` |
| `fina_audit` | 财务审计意见（意见 / 费用 / 事务所） | `financial_audit` | `financial_audit` | `financial_audit_strategy.py` | `audit` |
| `top10_holders` | 前十大股东 | `financial_shareholder` | `financial_shareholder_top10` | `financial_shareholder_strategy.py` | `shareholder` |
| `stk_holdernumber` | 股东户数 | `financial_stock_holder` | `financial_stock_holder` | `financial_stock_holder_strategy.py` | `stk_holder` |

### 2. `market_`（市场指标域）— 7 个数据源

| Tushare API | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|------------|------|------|---------|----------------|---------|
| `daily_basic` | 日频估值（PE / PB / PS / 市值 / 换手率） | `market_daily_basic` | `market_daily_basic` | `market_daily_basic_strategy.py` | `daily_basic` |
| `dividend` | 分红送股（现金分红 / 送转 / 除权除息日） | `market_dividend` | `market_dividend` | `market_dividend_strategy.py` | `dividend` |
| `moneyflow` | 资金流向（大 / 中 / 小 / 特大单买卖） | `market_moneyflow` | `market_moneyflow` | `market_moneyflow_strategy.py` | `moneyflow` |
| `margin_detail` | 融资融券明细（融资余额 / 融券余量） | `market_margin` | `market_margin_detail` | `market_margin_strategy.py` | `margin` |
| `hsgt_top10` | 沪深股通十大成交股 | `market_northbound` | `market_northbound_top10` | `market_northbound_strategy.py` | `hsgt` |
| `top_list` `top_inst` | 龙虎榜（交易明细 + 机构席位） | `market_dragon_tiger` | `market_dragon_tiger_list` `market_dragon_tiger_inst` | `market_dragon_tiger_strategy.py` | `dragon_tiger` |
| `block_trade` | 大宗交易明细 | `market_block_trade` | `market_block_trade` | `market_block_trade_strategy.py` | `block_trade` |

### 3. `kline_`（行情域）— 3 个数据源

| Tushare API | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|------------|------|------|---------|----------------|---------|
| `daily` / `adj_factor` / `stk_limit` | 日线 / 复权因子 / 涨跌停价 | `kline` | `kline_daily` | `kline_strategy.py` | `kline` |
| `stk_factor_pro` | 技术面因子（MACD / KDJ / RSI / BOLL / CCI 后复权） | `kline_stock_factor` | `kline_stock_factor` | `kline_stock_factor_strategy.py` | `stk_factor` |
| 内部因子管线（非 Tushare 直接数据源） | 因子元数据 / 因子计算 / 因子 Parquet 存储 | `kline_factor` | `factor_meta` `factor_latest` | `kline_factor_tushare_strategy.py` `kline_factor_compute_strategy.py` | `factor` |

### 4. `stock_`（股票基础域）— 3 个数据源

| Tushare API | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|------------|------|------|---------|----------------|---------|
| `stock_basic` | A 股股票列表 | `stock` | `stock_list` | `stock_strategy.py` | `stock` |
| — | 活跃股票数快照（未退市 / 应交易） | `stock` | `stock_active_count` | `stock_active_count_strategy.py` | — |
| `suspend_d` | 停复牌（S 停牌 / R 复牌） | `stock_suspend` | `stock_suspend` | `stock_suspend_strategy.py` | `suspend` |
| `trade_cal` | 全交易所交易日历 | `stock_trade_calendar` | `stock_trade_calendar` | `stock_trade_calendar_strategy.py` | `trade_cal` |

### 5. `index_`（指数域）— 1 个数据源

| Tushare API | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|------------|------|------|---------|----------------|---------|
| `index_weight` | 指数权重（沪深300 / 中证500 / 1000 / 创业板指） | `index_weight` | `index_weight` | `index_weight_strategy.py` | `index` |

### 6. `warehouse_`（仓库，独立）— 1 个数据源

| 数据来源 | 含义 | 前缀 | DB 表名 | strategy 文件名 | 旧模块名 |
|---------|------|------|---------|----------------|---------|
| PG `kline_daily` → Parquet | 日 K 列存导出 + PG 对账 | `warehouse` | Parquet 文件（无独立表） | `warehouse_kline_daily_strategy.py` | `warehouse` |

---

## 各层文件命名（以 `market_northbound` 为例）

文件放在对应域子目录下，如 `strategy/market/market_northbound_strategy.py`。

| 层 | 路径（相对于 `src/etl/`） | 职责 |
|----|--------|------|
| client | `client/market/market_northbound_tushare_client.py` | Tushare `hsgt_top10` API 调用 |
| extract | `extract/market/market_northbound_extract.py` | 远程数据源适配 |
| extract/local | `extract/local/market/market_northbound_local_extract.py` | 本地 DB 查询（max date / resolve 增量起点） |
| load | `load/market/market_northbound_load.py` | `bulk_upsert_postgresql` 入库 |
| workflow | `workflow/market/market_northbound_workflow.py` | Extract → Transform → Load 单次串联 |
| strategy | `market_northbound_strategy.py` | 区间编排 / 增量起点 / 宏观快照 / 微观补拉 |
| entity | `market_northbound_top10_entities.py` | SQLAlchemy ORM 实体 |

其他前缀同理：把 `market_northbound` 换成 `financial_forecast`、`kline_stock_factor` 等。

**特例**：`kline` 只有一个概念（日线+复权+涨跌停共享），直接用 `kline_strategy.py` 不加后缀概念。

---

## 命名规范

1. **模块名用规范英文**：`stock_factor` 不用 `stk_factor`，`trade_calendar` 不用 `trade_cal`，`northbound` 不用 `hsgt`，`stock_holder` 不用 `stk_holder`
2. **Tushare 原始接口名写文件头部注释**：`"""market_northbound — Tushare hsgt_top10 沪深股通十大成交股。"""`
3. **文件拼接规则**：`{域目录}/{域前缀}_{层后缀}.py`
   - `financial/financial_report_strategy.py` — Strategy 编排层
   - `market/market_northbound_workflow.py` — Workflow 单次执行
   - `kline/kline_load.py` — Load 入库
   - `stock/stock_extract.py` — Extract 远程拉取
   - `financial/financial_forecast_local_extract.py` — Extract 本地 DB 查询
   - `financial/financial_report_income_entities.py` — SQLAlchemy 实体
   - `market/market_northbound_tushare_client.py` — Tushare API 客户端
4. **域前缀拼接**：`{域}_{概念}` → `financial_forecast`、`market_northbound`、`stock_trade_calendar`
   - 单概念的域不加概念后缀：`kline_strategy.py`、`stock_strategy.py`
5. **CLI 子命令**按域分 Typer group：`financial`、`market`、`kline`、`stock`、`index`、`warehouse`

---

## 改动清单（从旧结构 → 新结构）

| # | 旧路径 | 新路径（strategy 层示例） | 说明 |
|---|-------|--------------------------|------|
| 1 | `stk_factor/stk_factor_strategy.py` | `kline/kline_stock_factor_strategy.py` | 改名 + 加行情域 |
| 2 | `stk_holder/stk_holdernumber_strategy.py` | `financial/financial_stock_holder_strategy.py` | 改名 + 加财务域 |
| 3 | `hsgt/hsgt_strategy.py` | `market/market_northbound_strategy.py` | 改名 + 加市场域 |
| 4 | `forecast/forecast_strategy.py` | `financial/financial_forecast_strategy.py` | 加财务域 |
| 5 | `express/express_strategy.py` | `financial/financial_express_strategy.py` | 加财务域 |
| 6 | `audit/audit_strategy.py` | `financial/financial_audit_strategy.py` | 加财务域 |
| 7 | `shareholder/shareholder_strategy.py` | `financial/financial_shareholder_strategy.py` | 加财务域 |
| 8 | `daily_basic/daily_basic_strategy.py` | `market/market_daily_basic_strategy.py` | 加市场域 |
| 9 | `dividend/dividend_strategy.py` | `market/market_dividend_strategy.py` | 加市场域 |
| 10 | `moneyflow/moneyflow_strategy.py` | `market/market_moneyflow_strategy.py` | 加市场域 |
| 11 | `margin/margin_strategy.py` | `market/market_margin_strategy.py` | 加市场域 |
| 12 | `suspend/suspend_strategy.py` | `stock/stock_suspend_strategy.py` | 加股票域 |
| 13 | `trade_cal/trade_cal_strategy.py` | `stock/stock_trade_calendar_strategy.py` | 改名 + 加股票域 |
| 14 | `financial/report_strategy.py` | `financial/financial_report_strategy.py` | 加域前缀 |
| 15 | `kline/kline_strategy.py` | `kline/kline_strategy.py` | 不改名 |
| 16 | `stock/stock_strategy.py` | `stock/stock_strategy.py` | 不改名 |
| 17 | `index/index_weight_strategy.py` | `index/index_weight_strategy.py` | 不改名 |
| 18 | `warehouse/kline_daily_warehouse_strategy.py` | `warehouse/warehouse_kline_daily_strategy.py` | 改后缀顺序 |

---

## 扩展预留（参考 Tushare API 文档）

Tushare 共有 237 个 API，当前接入 18 个。未来新增按域前缀直接加文件：

| 未来可能新增 | 域目录 | 域前缀 | 示例路径 |
|------------|--------|--------|----------|
| ETF 日线行情 (`fund_daily`) | `etf/` | `etf_` | `etf/etf_daily_strategy.py` |
| 公募基金净值 (`fund_nav`) | `fund/` | `fund_` | `fund/fund_nav_strategy.py` |
| 指数日线行情 (`index_daily`) | `index/` | `index_` | `index/index_daily_strategy.py` |
| 可转债基础信息 (`cb_basic`) | `bond/` | `bond_` | `bond/bond_convertible_strategy.py` |
| 期货日线 (`fut_daily`) | `future/` | `future_` | `future/future_daily_strategy.py` |
| 宏观经济 (`cn_cpi` 等) | `macro/` | `macro_` | `macro/macro_china_strategy.py` |
