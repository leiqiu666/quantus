# ETL 财报数据开发指南

本文档以 **income 利润表** 为例，完整梳理财报数据的开发流程、架构设计和关键实现细节，用于指导后续 **balance 资产负债表**、**cashflow 现金流量表** 等财报的快速开发。

---

## 📋 目录

1. [整体架构设计](#整体架构设计)
2. [开发流程概览](#开发流程概览)
3. [核心组件详解](#核心组件详解)
4. [数据流转过程](#数据流转过程)
5. [关键设计模式](#关键设计模式)
6. [开发 Checklist](#开发-checklist)
7. [新增财报表标准步骤](#新增财报表标准步骤)

---

## 整体架构设计

### 架构分层

```
CLI 层 (cli.py)
    ↓
Strategy 层 (report_strategy.py) - 业务编排
    ↓
Workflow 层 (report_workflow.py) - 工作流编排
    ↓
ETL 三层架构:
    ├── Extract 层 (report_extract.py) - 数据抽取
    ├── Transform 层 (report_transform.py) - 数据转换
    └── Load 层 (report_load.py) - 数据加载
    ↓
Model 层 (report_income_model.py) - 财报库表查询等
    ↓
Entities 层 (report_income_entities.py) - 数据模型（ORM）
```

### 目录结构

```
src/etl/
├── cli.py                          # CLI 命令行入口
├── extract/
│   └── tushare/
│       └── report_extract.py       # Tushare 数据抽取器
├── transform/
│   └── financial/
│       └── report_transform.py     # 数据转换器
├── load/
│   └── financial/
│       └── report_load.py          # 数据加载器
├── workflow/
│   └── financial/
│       └── report_workflow.py      # 工作流编排器
├── strategy/
│   └── financial/
│       └── report_strategy.py      # 策略编排器
└── log/
    └── missing_log.py              # 缺失日志记录
```

---

## 开发流程概览

### Income 利润表完整开发流程

```
1. 定义数据模型 (Entities)
   └─ report_income_entities.py

2. 实现数据抽取 (Extract)
   └─ report_extract.py

3. 实现数据转换 (Transform)
   └─ report_transform.py

4. 实现数据加载 (Load)
   └─ report_load.py

5. 实现 Model 查询 (Model)
   └─ report_income_model.py

6. 编排工作流 (Workflow)
   └─ report_workflow.py

7. 编排策略 (Strategy)
   └─ report_strategy.py

8. 注册 CLI 命令 (CLI)
   └─ cli.py
```

---

## 核心组件详解

### 1. Entities 层 - 数据模型定义

**文件**: `src/entities/data_entities/report_income_entities.py`

**核心职责**:
- 定义 SQLAlchemy ORM 模型
- 映射数据库表结构
- 定义索引和唯一约束

**关键设计**:

```python
class ReportIncomeEntities(Base):
    __tablename__ = "report_income"
    
    # 1. 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 2. 核心维度字段（用于查询和关联）
    ts_code = Column(String(20))          # 股票代码
    end_date = Column(String(8))          # 报告期 YYYYMMDD
    report_type = Column(String(20))      # 报表类型
    f_ann_date = Column(String(8))        # 实际公告日期
    update_flag = Column(String(1))       # 更新标志
    
    # 3. 核心指标字段（常用查询指标独立建字段）
    total_revenue = Column(Float)         # 营业总收入
    total_cogs = Column(Float)            # 营业总成本
    operate_profit = Column(Float)        # 营业利润
    n_income = Column(Float)              # 净利润
    # ... 更多指标
    
    # 4. JSONB 字段（存储所有非核心字段）
    income_table = Column(JSONB)          # 利润表完整详情
    
    # 5. 复合唯一索引（用于 upsert 冲突检测）
    __table_args__ = (
        Index('idx_report_income_upsert_key', 
              'ts_code', 'end_date', 'f_ann_date', 'report_type', 'update_flag', 
              unique=True),
        # ... 其他业务索引
    )
```

**设计要点**:
- ✅ 核心字段独立列存储（便于查询和索引）
- ✅ 非核心字段统一存入 JSONB（灵活扩展）
- ✅ 复合唯一索引确保数据唯一性（upsert 依赖）
- ✅ 为常用查询字段单独建索引

---

### 2. Extract 层 - 数据抽取

**文件**: `src/etl/extract/tushare/report_extract.py`

**核心职责**:
- 调用 Tushare API 获取原始数据
- 实现限流控制
- 返回 DataFrame

**关键实现**:

```python
class ReportExtract:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts
    
    def pull_report_income_by_code(self, ts_code: str, **kwargs):
        """按股票代码拉取（用于补数据）"""
        report_income = self.ts.income(ts_code=ts_code, **kwargs)
        return report_income
    
    def pull_report_income(self, **kwargs):
        """按期次拉取（用于批量入库）"""
        _acquire_income_vip_rate_limit()  # 限流控制
        report_income = self.ts.income_vip(**kwargs)
        return report_income

# 限流器定义（模块级别）
_acquire_income_vip_rate_limit = create_rate_limiter(400)
```

**设计要点**:
- ✅ 两种拉取方式：按 period（批量）和按 ts_code（单股补数据）
- ✅ 限流保护：使用 `create_rate_limiter(400)` 控制 API 调用频率
- ✅ 返回原始 DataFrame，不做清洗

---

### 3. Transform 层 - 数据转换

**文件**: `src/etl/transform/financial/report_transform.py`

**核心职责**:
- 数据清洗和去重
- 报告类型统一映射
- 将非核心字段转为 JSONB

**关键方法**:

#### 3.1 数据清洗 `report_transform_merge_now`

```python
@staticmethod
def report_transform_merge_now(report_income_df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗规则（保证 ts_code + end_date + report_type 唯一）:
        1. 同一 (ts_code, end_date, report_type) 有多条时，优先保留 update_flag == '1'
        2. 若 update_flag == '1' 仍有多条，则保留 f_ann_date 最大的一条
        3. 若没有 update_flag == '1'，则保留 f_ann_date 最大的一条
        4. 最终将所有记录的 report_type 统一改为 "merge_now"
    """
    # 排序优先级：同组内先 update_flag=='1'，再 f_ann_date 最大
    df["_update_flag_is_1"] = (df["update_flag"].astype(str) == "1").astype(int)
    df["_f_ann_date_norm"] = df["f_ann_date"].fillna("").astype(str)
    
    df = df.sort_values(
        by=["ts_code", "end_date", "report_type", "_update_flag_is_1", "_f_ann_date_norm"],
        ascending=[True, True, True, False, False],
        kind="mergesort",
    )
    
    # 按 (ts_code, end_date, report_type) 去重保留首条
    df = df.drop_duplicates(subset=["ts_code", "end_date", "report_type"], keep="first")
    
    # 映射为 merge_now
    df["report_type"] = "merge_now"
    
    # 清理临时列
    df = df.drop(columns=["_update_flag_is_1", "_f_ann_date_norm"])
    
    return df
```

**设计要点**:
- ✅ 优先级去重策略（update_flag > f_ann_date）
- ✅ 统一映射为 `merge_now`（简化后续查询）
- ✅ 稳定排序（`mergesort`）保证可复现
- ✅ 严格校验唯一性

#### 3.2 JSONB 转换 `report_more_detail_to_json`

```python
@staticmethod
def report_more_detail_to_json(data_model: Type[Any], tushare_data: pd.DataFrame) -> pd.DataFrame:
    """
    将 tushare 数据中非核心字段转换为 JSON 格式
    
    逻辑:
    1. 识别 data_model 中定义的字段（排除 JSONB 字段）
    2. 在 tushare_data 中删除表结构中存在的字段
    3. 将剩下的字段改成 json 格式，存储在 PostgreSQL 的 jsonb 字段中
    """
    # 获取模型定义的字段和 JSONB 字段
    model_columns = set()
    jsonb_column = None
    
    for col in data_model.__table__.columns:
        col_type_str = str(col.type).upper()
        if "JSONB" in col_type_str or "JSON" in col_type_str:
            jsonb_column = col.name
        else:
            model_columns.add(col_name)
    
    # 找出需要转 JSON 的字段
    tushare_columns = set(tushare_data.columns)
    json_columns = tushare_columns - model_columns - {jsonb_column}
    
    # 逐行转换
    json_data_list = []
    for _, row in tushare_data.iterrows():
        json_dict = {}
        for col in json_columns:
            value = row[col]
            if pd.isna(value) or value is None or (isinstance(value, str) and value.strip() == ""):
                continue
            json_dict[col] = value
        json_data_list.append(json_dict)
    
    result_df[jsonb_column] = json_data_list
    
    # 只保留模型字段和 JSONB 字段
    columns_to_keep = model_columns | {jsonb_column}
    result_df = result_df[[col for col in columns_to_keep if col in result_df.columns]]
    
    return result_df
```

**设计要点**:
- ✅ 自动识别模型字段和 JSONB 字段
- ✅ 智能过滤空值（NaN、None、空字符串）
- ✅ 最终只保留模型定义字段 + JSONB 字段

#### 3.3 报告期生成 `report_period_generate`

```python
def report_period_generate(self, start_date: str, end_date: str) -> List[str]:
    """生成财报报告期列表"""
    QUARTER_END_DATES = ("0331", "0630", "0930", "1231")
    
    for year in range(start_year, end_year + 1):
        for qend in QUARTER_END_DATES:
            period = f"{year}{qend}"
            if start_date <= period <= end_date:
                report_period.append(period)
    
    return report_period
```

#### 3.4 完整性检查 `check_report_complete_by_ts_code`

```python
def check_report_complete_by_ts_code(
    self,
    end_dates: list[str],
    start_end_date: str,
    end_end_date: str,
) -> list[str]:
    """
    对比已有报告期，返回缺失的报告期列表
    
    适用于利润表、现金流、资产负债表等任意「报告期列为季度末」的表
    """
    expected = self.report_period_generate(start_end_date, end_end_date)
    missing_periods = [ed for ed in expected if ed not in end_dates]
    return missing_periods
```

---

### 4. Load 层 - 数据加载

**文件**: `src/etl/load/financial/report_load.py`

**核心职责**:
- DataFrame 批量写入 PostgreSQL
- **`load_report`**：直接 `bulk_upsert_postgresql`（快照表等）
- **`load_report_filter`**：先查再改再插；查库经 `LocalReportExtract → ReportService → Model`（见 [`spec/load/存储-先查再改再插.sdd.md`](../../spec/load/存储-先查再改再插.sdd.md)）。三表 `by_period` / `by_ts_code` 已接入。

**日 K**（[`kline_load.py`](load/kline/kline_load.py)）：`pull_kline_daily_by_date` 使用 **`load_kline_daily_filter`**（查库经 `KlineLocalExtract`）；按股区间补拉仍用 `load_kline_daily`。

**关键实现**:

```python
class ReportLoad:
    def __init__(self):
        self.db = Database()
    
    def load_report(self, entities: Type[Any], df: pd.DataFrame, *, verbose: bool = False) -> int:
        """
        将清洗后的 DataFrame 批量写入 PostgreSQL
        
        Args:
            entities: SQLAlchemy 实体类（表模型）
            df: 待入库的数据表
            verbose: 是否输出调试信息
        
        Returns:
            实际写入/更新的记录数
        """
        if df is None or df.empty:
            return 0
        
        # DataFrame -> List[Dict]，并处理 NaN 为 None
        records = dataframe_to_list(df)
        
        # 使用 bulk_upsert_postgresql 进行批量插入/更新
        # 冲突键使用实体类上定义的唯一索引
        saved_count = self.db.bulk_upsert_postgresql(
            model_class=entities,
            records=records,
            conflict_keys=None,  # 使用模型定义的唯一索引
            fallback_on_error=True,
        )
        
        return saved_count
```

**设计要点**:
- ✅ 统一的上写接口（适用于所有财报表）
- ✅ 自动处理 NaN → None
- ✅ 批量 upsert（性能优化）
- ✅ 错误回退机制

---

### 5. Model 层 - 财报库表访问

**文件**: `src/model/financial/report_income_model.py`

**核心职责**:
- 提供财报数据的库表查询（含按代码、全量按列裁剪等）

**关键实现**:

```python
class ReportIncomeModel:
    def __init__(self):
        self.db = Database()

    def get_report_income_by_ts_code(self, ts_code: str, **kwargs):
        """
        根据股票代码获取财报数据
        
        Returns:
            财报数据（ORM 实例列表）
        """
        return self.db.get_all(ReportIncomeEntities, ts_code=ts_code, **kwargs)
```

**设计要点**:
- ✅ 返回 ORM 实例（非字典）
- ✅ 支持额外查询条件（**kwargs）；全量可查 `get_report_income_all(return_fields=(...))`

---

### 6. Workflow 层 - 工作流编排

**文件**: `src/etl/workflow/financial/report_workflow.py`

**核心职责**:
- 串联 Extract → Transform → Load
- 实现完整性检查和补数据逻辑

**关键方法**:

#### 6.1 按期次入库 `report_income_by_period`

```python
def report_income_by_period(self, period: str) -> int:
    """
    按期次批量入库（用于历史数据初始化）
    """
    # Step 1: 抽取
    report_income = self.report_extract.pull_report_income(period=period)
    
    # Step 2: 转换
    report_income_cleaned = self.report_transform.report_transform_merge_now(report_income)
    report_income_cleaned_json = self.report_transform.report_more_detail_to_json(
        ReportIncomeEntities, report_income_cleaned
    )
    
    # Step 3: 加载
    saved_count = self.report_load.load_report(
        entities=ReportIncomeEntities,
        df=report_income_cleaned_json,
    )
    
    return saved_count
```

#### 6.2 按个股补数据 `report_income_by_ts_code`

```python
def report_income_by_ts_code(self, ts_code: str, end_date: str) -> int:
    """
    按个股+报告期补数据（用于缺失数据补录）
    """
    # 拉取财报数据
    report_income = self.report_extract.pull_report_income_by_code(
        ts_code=ts_code, end_date=end_date
    )
    # 清洗财报数据
    report_income_cleaned = self.report_transform.report_transform_merge_now(report_income)
    # 将财报数据转换为 JSON 格式
    report_income_cleaned_json = self.report_transform.report_more_detail_to_json(
        ReportIncomeEntities, report_income_cleaned
    )
    # 保存财报数据
    saved_count = self.report_load.load_report(
        entities=ReportIncomeEntities, df=report_income_cleaned_json
    )
    return saved_count
```

#### 6.3 完整性检查与补数据 `check_report_income_complete_by_ts_code`

```python
def check_report_income_complete_by_ts_code(
    self,
    ts_code: str,
    start_end_date: str | None = None,
    end_end_date: str | None = None,
) -> list[str]:
    """
    检查财报数据完整性，自动补数据并记录缺失日志
    """
    if end_end_date is None:
        end_end_date = datetime.now().strftime("%Y%m%d")
    if start_end_date is None:
        start_end_date = "20050101"
    
    # Step 1: 获取已有数据
    report_income = self.report_income_model.get_report_income_by_ts_code(ts_code=ts_code)
    end_dates = [r.end_date for r in report_income]
    
    # Step 2: 检查缺失报告期
    missing_periods = self.report_transform.check_report_complete_by_ts_code(
        end_dates=end_dates,
        start_end_date=start_end_date,
        end_end_date=end_end_date,
    )
    
    # Step 3: 记录缺失日志
    missing_items = [f"{ts_code},{ed}" for ed in missing_periods]
    self.missing_log.upsert_missing_logs(
        missing_items=missing_items, missing_entity="report_income"
    )
    
    # Step 4: 补拉缺失数据
    for period in missing_periods:
        report_income = self.report_income_by_ts_code(ts_code=ts_code, end_date=period)
        if report_income == 0:
            # 拉取失败，登记 / try_count++
            self.missing_log.upsert_missing_logs(
                missing_items=[f"{ts_code},{period}"], missing_entity="report_income"
            )
        else:
            # 拉取成功，物理删除登记
            self.missing_log.delete_missing_logs(
                missing_items=[f"{ts_code},{period}"],
                missing_entity="report_income",
            )
    
    return missing_periods
```

**设计要点**:
- ✅ 三种工作流模式：批量入库、单股补数据、完整性检查
- ✅ 缺失日志登记/解除（成功即删，失败留底）
- ✅ 自动重试机制

---

### 7. Strategy 层 - 策略编排

**文件**: `src/etl/strategy/financial/report_strategy.py`

**核心职责**:
- 高层业务策略编排
- 批量任务调度

**关键方法**:

#### 7.1 历史全量入库 `report_income_history_init`

```python
def report_income_history_init(self):
    """历史利润表全量入库（从 1990 年至今）"""
    today = datetime.now().strftime("%Y%m%d")
    report_period = report_period_generate(start_date='19900101', end_date=today)
    
    pbar = tqdm_iter(report_period, desc="历史利润表income入库", unit="期")
    for period in pbar:
        saved_count = self.report_workflow.report_income_by_period(period=period)
        pbar.set_postfix(saved=saved_count)
    
    return report_period
```

#### 7.2 测试入库 `report_income_test_init`

```python
def report_income_test_init(self):
    """测试入库（从 2024 年至今）"""
    today = datetime.now().strftime("%Y%m%d")
    report_period = report_period_generate(start_date='20240101', end_date=today)
    
    pbar = tqdm_iter(report_period, desc="历史利润表income入库", unit="期")
    for period in pbar:
        saved_count = self.report_workflow.report_income_by_period(period=period)
        pbar.set_postfix(saved=saved_count)
    
    return report_period
```

#### 7.3 完整性检查 `check_report_complete_history`

```python
def check_report_complete_history(self):
    """检查所有股票财报完整性"""
    # Step 1: 获取所有股票列表
    stock_list = self.stock_base_service.get_all_stock_list_a()
    missing_all: list[str] = []
    
    pbar = tqdm_iter(stock_list, desc="检查财报完整性", unit="股票")
    for inst in pbar:
        ts_code = getattr(inst, "ts_code", None)
        list_date = getattr(inst, "list_date", None)
        start_date = max("20050101", list_date)
        
        # Step 2: 检查单股完整性
        missing_periods = self.report_workflow.check_report_income_complete_by_ts_code(
            ts_code=ts_code,
            start_end_date=start_date,
            end_end_date=datetime.now().strftime("%Y%m%d"),
        )
        missing_all.extend(f"{ts_code},{ed}" for ed in missing_periods)
        pbar.set_postfix(saved=len(missing_periods))
    
    return len(missing_all)
```

**设计要点**:
- ✅ 进度条展示（tqdm）
- ✅ 实时反馈（set_postfix）
- ✅ 批量任务调度

---

### 8. CLI 层 - 命令行入口

**文件**: `src/etl/cli.py`

**核心职责**:
- 提供交互式命令行菜单
- 注册 Typer 命令

**关键实现**:

```python
import typer
import questionary
from src.etl.strategy.financial.report_strategy import ReportStrategy

app = typer.Typer()
report_strategy = typer.Typer()
app.add_typer(report_strategy, name="report", help="Report strategy commands")

# 菜单处理器
_MENU_HANDLERS: dict[str, Callable[[], None]] = {
    "income-history-init": lambda: ReportStrategy().report_income_history_init(),
    "income-test-init": lambda: ReportStrategy().report_income_test_init(),
    "check-income-complete": lambda: ReportStrategy().check_report_complete_history(),
}

# 菜单项
_MENU_ROWS: list[tuple[str, str]] = [
    ("历史利润表 income 全量入库 (report income-history-init)", "income-history-init"),
    ("历史利润表 income 测试入库 (report income-test-init)", "income-test-init"),
    ("检查历史利润表 income 完整性 (report check-income-complete)", "check-income-complete"),
]

# 注册命令
@report_strategy.command("income-history-init")
def income_history_init():
    report_strategy = ReportStrategy()
    report_strategy.report_income_history_init()

@report_strategy.command("income-test-init")
def income_test_init():
    report_strategy = ReportStrategy()
    report_strategy.report_income_test_init()

@report_strategy.command("check-income-complete")
def check_income_complete():
    report_strategy = ReportStrategy()
    report_strategy.check_report_complete_history()
```

**使用方式**:
```bash
# 交互式菜单
python -m src.etl.cli

# 直接命令
python -m src.etl.cli report income-history-init
python -m src.etl.cli report income-test-init
python -m src.etl.cli report check-income-complete
```

---

## 数据流转过程

### 完整数据流

```
Tushare API
    ↓ (income_vip)
[Extract] pull_report_income(period="20240331")
    ↓ (DataFrame)
[Transform] report_transform_merge_now()
    ↓ (清洗后 DataFrame)
[Transform] report_more_detail_to_json(ReportIncomeEntities)
    ↓ (核心字段 + JSONB 字段)
[Load] load_report(ReportIncomeEntities, df)
    ↓ (bulk_upsert_postgresql)
PostgreSQL (report_income 表)
```

### 缺失数据补录流

```
[Strategy] check_report_complete_history()
    ↓ (遍历所有股票)
[Workflow] check_report_income_complete_by_ts_code(ts_code)
    ↓
[Model] get_report_income_by_ts_code(ts_code)
    ↓ (已有 end_date 列表)
[Transform] check_report_complete_by_ts_code()
    ↓ (缺失 period 列表)
[Log] upsert_missing_logs()
    ↓
[Workflow] report_income_by_ts_code(ts_code, period)
    ↓ (逐个补拉)
[Extract] pull_report_income_by_code(ts_code, end_date)
    ↓
[Transform] → [Load] → PostgreSQL
```

---

## 关键设计模式

### 1. 数据模型设计模式

**核心字段 + JSONB 混合存储**

```
┌─────────────────────────────────────┐
│         核心字段（独立列）            │
│  - ts_code (查询维度)                │
│  - end_date (查询维度)               │
│  - report_type (查询维度)            │
│  - total_revenue (常用指标)          │
│  - n_income (常用指标)               │
│  ...                                 │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│       JSONB 字段（灵活扩展）          │
│  {                                   │
│    "ebit": 123.45,                   │
│    "ebitda": 234.56,                 │
│    "dt_netprofit": 345.67,           │
│    ... (所有非核心字段)              │
│  }                                   │
└─────────────────────────────────────┘
```

**优势**:
- ✅ 核心字段高性能查询（B-Tree 索引）
- ✅ JSONB 灵活扩展（无需改表结构）
- ✅ 兼顾查询性能和灵活性

### 2. 去重策略模式

**优先级去重规则**:
```
同一 (ts_code, end_date, report_type) 有多条记录时:
  1. 优先保留 update_flag == '1'（已更新）
  2. 若 update_flag 相同，保留 f_ann_date 最大（最新公告）
  3. 最终统一映射为 report_type = 'merge_now'
```

**实现技巧**:
```python
# 临时标记
df["_update_flag_is_1"] = (df["update_flag"].astype(str) == "1").astype(int)
df["_f_ann_date_norm"] = df["f_ann_date"].fillna("").astype(str)

# 多字段排序
df = df.sort_values(
    by=["ts_code", "end_date", "report_type", "_update_flag_is_1", "_f_ann_date_norm"],
    ascending=[True, True, True, False, False],
    kind="mergesort",
)

# 去重保留首条
df = df.drop_duplicates(subset=["ts_code", "end_date", "report_type"], keep="first")
```

### 3. Upsert 模式

**依赖复合唯一索引**:
```python
__table_args__ = (
    Index('idx_report_income_upsert_key', 
          'ts_code', 'end_date', 'f_ann_date', 'report_type', 'update_flag', 
          unique=True),
)
```

**批量 upsert**:
```python
saved_count = self.db.bulk_upsert_postgresql(
    model_class=ReportIncomeEntities,
    records=records,
    conflict_keys=None,  # 使用模型定义的唯一索引
    fallback_on_error=True,
)
```

### 4. 缺失日志模式

**日志表结构**:
```python
class LogMissing(Base):
    ts_code = Column(String(20))
    missing_entity = Column(String(100))  # "report_income"
    missing_date = Column(String(8))
    try_count = Column(Integer)
    last_try_time = Column(DateTime)
    
    __table_args__ = (
        Index('idx_log_missing_unique', 
              'ts_code', 'missing_entity', 'missing_date', 
              unique=True),
    )
```

> 详见 [`spec/etl/log-缺失日志.sdd.md`](../../spec/etl/log-缺失日志.sdd.md)。表里的每行都是「至今未补入库」的待办，补入成功后**物理删除**。

**日志更新策略**:
```python
# 拉取失败：登记 / try_count 自动 +1
self.missing_log.upsert_missing_logs(
    missing_items=[f"{ts_code},{period}"], 
    missing_entity="report_income",
)

# 拉取成功：物理删除登记
self.missing_log.delete_missing_logs(
    missing_items=[f"{ts_code},{period}"],
    missing_entity="report_income",
)
```

---

## 开发 Checklist

开发新财报表（如 balance 资产负债表）时，按以下清单逐项完成：

### Phase 1: 数据模型 (Entities)
- [ ] 创建 `report_balance.entities.py`
- [ ] 定义所有字段（参考 Tushare 文档）
- [ ] 区分核心字段和 JSONB 字段
- [ ] 定义复合唯一索引（ts_code + end_date + f_ann_date + report_type + update_flag）
- [ ] 为常用查询字段建索引
- [ ] 执行 `python report_balance.entities.py` 创建表

### Phase 2: Extract 层
- [ ] 在 `report_extract.py` 中添加 `pull_report_balance()` 方法
- [ ] 在 `report_extract.py` 中添加 `pull_report_balance_by_code()` 方法
- [ ] 添加限流器（参考 `_acquire_income_vip_rate_limit`）
- [ ] 测试数据拉取

### Phase 3: Transform 层
- [ ] Transform 层逻辑可复用（无需修改）
- [ ] 验证 `report_transform_merge_now()` 通用性
- [ ] 验证 `report_more_detail_to_json()` 通用性

### Phase 4: Load 层
- [ ] Load 层逻辑可复用（无需修改）
- [ ] 验证 `load_report()` 通用性

### Phase 5: Model 层
- [ ] 在 `report_balance_model.py` 中实现 `get_report_balance_by_ts_code()`、`get_report_balance_all()`（若尚未实现）
- [ ] 测试查询功能

### Phase 6: Workflow 层
- [ ] 在 `report_workflow.py` 中添加 `report_balance_by_period()` 方法
- [ ] 在 `report_workflow.py` 中添加 `report_balance_by_ts_code()` 方法
- [ ] 在 `report_workflow.py` 中添加 `check_report_balance_complete_by_ts_code()` 方法
- [ ] 导入 `ReportBalanceEntities`
- [ ] 导入 `ReportBalanceModel`（完整性检查等读库逻辑走 Model）
- [ ] 测试完整工作流

### Phase 7: Strategy 层
- [ ] 在 `report_strategy.py` 中添加 `report_balance_history_init()` 方法
- [ ] 在 `report_strategy.py` 中添加 `report_balance_test_init()` 方法
- [ ] 在 `report_strategy.py` 中添加 `check_balance_complete_history()` 方法
- [ ] 导入 `ReportBalanceWorkflow`
- [ ] 测试策略编排

### Phase 8: CLI 层
- [ ] 在 `cli.py` 中添加菜单项到 `_MENU_ROWS`
- [ ] 在 `cli.py` 中添加处理器到 `_MENU_HANDLERS`
- [ ] 注册 Typer 命令（`@report_strategy.command`）
- [ ] 测试交互式菜单
- [ ] 测试直接命令

### Phase 9: 验证测试
- [ ] 测试历史全量入库
- [ ] 测试单股补数据
- [ ] 测试完整性检查
- [ ] 测试缺失日志记录
- [ ] 验证 upsert 逻辑
- [ ] 验证 JSONB 字段内容

---

## 新增财报表标准步骤

以 **balance 资产负债表** 为例，给出具体实现步骤：

### Step 1: 确认实体类已创建

**检查**: `src/entities/data_entities/report_balance.entities.py`

**已完成**: ✅ 该文件已存在，包含完整的字段定义

### Step 2: Extract 层扩展

**文件**: `src/etl/extract/tushare/report_extract.py`

**需要添加**:
```python
# 限流器（与其他报表共用）
# _acquire_income_vip_rate_limit 已定义，可复用

def pull_report_balance(self, **kwargs):
    """按期次拉取资产负债表"""
    _acquire_income_vip_rate_limit()
    report_balance = self.ts.balancesheet_vip(**kwargs)
    return report_balance

def pull_report_balance_by_code(self, ts_code: str, **kwargs):
    """按股票代码拉取资产负债表"""
    report_balance = self.ts.balancesheet(ts_code=ts_code, **kwargs)
    return report_balance
```

### Step 3: Model 层查询方法

**文件**: `src/model/financial/report_balance_model.py`

**示例**（与利润表 Model 一致的模式）:
```python
from src.entities.data_entities.report_balance_entities import ReportBalanceEntities
from src.common.database import Database

class ReportBalanceModel:
    def __init__(self):
        self.db = Database()

    def get_report_balance_by_ts_code(self, ts_code: str, **kwargs):
        """根据股票代码获取资产负债表数据（ORM 列表）"""
        return self.db.get_all(ReportBalanceEntities, ts_code=ts_code, **kwargs)
```

### Step 4: Workflow 层扩展

**文件**: `src/etl/workflow/financial/report_workflow.py`

**需要添加的导入**:
```python
from src.entities.data_entities.report_balance_entities import ReportBalanceEntities
from src.model.financial.report_balance_model import ReportBalanceModel
```

**需要添加的初始化**:
```python
class ReportWorkflow:
    def __init__(self):
        # ... 现有代码 ...
        self.report_balance_model = ReportBalanceModel()
```

**需要添加的方法**:
```python
def report_balance_by_period(self, period: str) -> int:
    """按期次批量入库资产负债表"""
    report_balance = self.report_extract.pull_report_balance(period=period)
    report_balance_cleaned = self.report_transform.report_transform_merge_now(report_balance)
    report_balance_cleaned_json = self.report_transform.report_more_detail_to_json(
        ReportBalanceEntities, report_balance_cleaned
    )
    saved_count = self.report_load.load_report(
        entities=ReportBalanceEntities,
        df=report_balance_cleaned_json,
    )
    return saved_count

def report_balance_by_ts_code(self, ts_code: str, end_date: str) -> int:
    """按个股+报告期补数据"""
    report_balance = self.report_extract.pull_report_balance_by_code(
        ts_code=ts_code, end_date=end_date
    )
    report_balance_cleaned = self.report_transform.report_transform_merge_now(report_balance)
    report_balance_cleaned_json = self.report_transform.report_more_detail_to_json(
        ReportBalanceEntities, report_balance_cleaned
    )
    saved_count = self.report_load.load_report(
        entities=ReportBalanceEntities, df=report_balance_cleaned_json
    )
    return saved_count

def check_report_balance_complete_by_ts_code(
    self,
    ts_code: str,
    start_end_date: str | None = None,
    end_end_date: str | None = None,
) -> list[str]:
    """检查资产负债表完整性"""
    if end_end_date is None:
        end_end_date = datetime.now().strftime("%Y%m%d")
    if start_end_date is None:
        start_end_date = "20050101"
    
    report_balance = self.report_balance_model.get_report_balance_by_ts_code(ts_code=ts_code)
    end_dates = [r.end_date for r in report_balance]
    
    missing_periods = self.report_transform.check_report_complete_by_ts_code(
        end_dates=end_dates,
        start_end_date=start_end_date,
        end_end_date=end_end_date,
    )
    
    missing_items = [f"{ts_code},{ed}" for ed in missing_periods]
    self.missing_log.upsert_missing_logs(
        missing_items=missing_items, missing_entity="report_balance"
    )
    
    for period in missing_periods:
        report_balance = self.report_balance_by_ts_code(ts_code=ts_code, end_date=period)
        if report_balance == 0:
            self.missing_log.upsert_missing_logs(
                missing_items=[f"{ts_code},{period}"], missing_entity="report_balance"
            )
        else:
            self.missing_log.delete_missing_logs(
                missing_items=[f"{ts_code},{period}"],
                missing_entity="report_balance",
            )
    
    return missing_periods
```

### Step 5: Strategy 层扩展

**文件**: `src/etl/strategy/financial/report_strategy.py`

**需要添加的方法**:
```python
def report_balance_history_init(self):
    """历史资产负债表全量入库"""
    today = datetime.now().strftime("%Y%m%d")
    report_period = report_period_generate(start_date='19900101', end_date=today)
    pbar = tqdm_iter(report_period, desc="历史资产负债表balance入库", unit="期")
    for period in pbar:
        saved_count = self.report_workflow.report_balance_by_period(period=period)
        pbar.set_postfix(saved=saved_count)
    return report_period

def report_balance_test_init(self):
    """测试入库"""
    today = datetime.now().strftime("%Y%m%d")
    report_period = report_period_generate(start_date='20240101', end_date=today)
    pbar = tqdm_iter(report_period, desc="历史资产负债表balance入库", unit="期")
    for period in pbar:
        saved_count = self.report_workflow.report_balance_by_period(period=period)
        pbar.set_postfix(saved=saved_count)
    return report_period

def check_balance_complete_history(self):
    """检查所有股票资产负债表完整性"""
    stock_list = self.stock_base_service.get_all_stock_list_a()
    missing_all: list[str] = []
    pbar = tqdm_iter(stock_list, desc="检查资产负债表完整性", unit="股票")
    for inst in pbar:
        ts_code = getattr(inst, "ts_code", None)
        list_date = getattr(inst, "list_date", None)
        start_date = max("20050101", list_date)
        missing_periods = self.report_workflow.check_report_balance_complete_by_ts_code(
            ts_code=ts_code,
            start_end_date=start_date,
            end_end_date=datetime.now().strftime("%Y%m%d"),
        )
        missing_all.extend(f"{ts_code},{ed}" for ed in missing_periods)
        pbar.set_postfix(saved=len(missing_periods))
    return len(missing_all)
```

### Step 6: CLI 层注册

**文件**: `src/etl/cli.py`

**需要添加的代码**:

```python
# 添加到 _MENU_HANDLERS
_MENU_HANDLERS: dict[str, Callable[[], None]] = {
    # ... 现有代码 ...
    "balance-history-init": lambda: ReportStrategy().report_balance_history_init(),
    "balance-test-init": lambda: ReportStrategy().report_balance_test_init(),
    "check-balance-complete": lambda: ReportStrategy().check_balance_complete_history(),
}

# 添加到 _MENU_ROWS
_MENU_ROWS: list[tuple[str, str]] = [
    # ... 现有代码 ...
    ("历史资产负债表 balance 全量入库 (report balance-history-init)", "balance-history-init"),
    ("历史资产负债表 balance 测试入库 (report balance-test-init)", "balance-test-init"),
    ("检查历史资产负债表 balance 完整性 (report check-balance-complete)", "check-balance-complete"),
]

# 注册命令
@report_strategy.command("balance-history-init")
def balance_history_init():
    report_strategy = ReportStrategy()
    report_strategy.report_balance_history_init()

@report_strategy.command("balance-test-init")
def balance_test_init():
    report_strategy = ReportStrategy()
    report_strategy.report_balance_test_init()

@report_strategy.command("check-balance-complete")
def check_balance_complete():
    report_strategy = ReportStrategy()
    report_strategy.check_balance_complete_history()
```

---

## 核心设计原则总结

### 1. 分层职责明确
- **Extract**: 只负责拉取原始数据
- **Transform**: 只负责数据清洗和转换
- **Load**: 只负责数据入库
- **Workflow**: 串联 ETL 流程
- **Strategy**: 高层业务编排
- **CLI**: 用户交互入口

### 2. 高度复用
- Transform 和 Load 层完全通用，无需为每张表重写
- Workflow 层只需复制方法并替换实体类和服务类
- Strategy 层只需复制方法并替换 Workflow 调用

### 3. 灵活扩展
- JSONB 字段支持动态扩展，无需改表结构
- 核心字段独立存储，保证查询性能
- 缺失日志机制支持自动重试

### 4. 容错机制
- 限流保护（避免 API 超限）
- 缺失日志（记录失败，便于重试）
- Upsert 策略（避免重复数据）
- 错误回退（fallback_on_error）

### 5. 可观测性
- 进度条展示（tqdm）
- 实时反馈（set_postfix）
- 缺失日志（try_count、last_try_time）

---

## 快速开发模板

### 新增财报表最小改动清单

| 层级 | 文件 | 改动类型 | 工作量 |
|------|------|----------|--------|
| Entities | `report_xxx.entities.py` | 已创建 | ✅ 完成 |
| Extract | `report_extract.py` | 添加 2 个方法 | ⚡ 5 分钟 |
| Transform | `report_transform.py` | 无需改动 | ✅ 复用 |
| Load | `report_load.py` | 无需改动 | ✅ 复用 |
| Service | `report_xxx_service.py` | 创建新文件 | ⚡ 10 分钟 |
| Workflow | `report_workflow.py` | 添加 3 个方法 | ⚡ 15 分钟 |
| Strategy | `report_strategy.py` | 添加 3 个方法 | ⚡ 10 分钟 |
| CLI | `cli.py` | 添加 3 个命令 | ⚡ 5 分钟 |

**总计**: 约 45 分钟即可完成一张新财报表的开发 🚀

---

## 常见问题 FAQ

### Q1: 为什么核心字段要独立存储，而不是全部用 JSONB？
**A**: 核心字段（如 ts_code、end_date、total_revenue）需要频繁查询和聚合，独立列 + B-Tree 索引性能远高于 JSONB 查询。JSONB 适合存储不常查询的明细字段。

### Q2: 为什么 report_type 要统一映射为 "merge_now"？
**A**: Tushare 返回的 report_type 有多种类型（合并报表、单季合并等），业务上通常只需要最新合并报表。统一映射后，查询逻辑大幅简化。

### Q3: 如果 Tushare API 字段变更怎么办？
**A**: JSONB 字段天然支持字段变更，无需改表结构。只需在 Transform 层验证新字段是否存在即可。

### Q4: 如何批量重试缺失数据？
**A**: `log_missing` 表里的每行都是待补拉的（成功项已物理删除）。按 `missing_entity` 过滤后逐行调用 `report_income_by_ts_code()` 等补拉方法即可；成功后调 `delete_missing_logs(...)` 解除登记。

### Q5: 为什么使用 upsert 而不是 insert？
**A**: 财报数据可能多次更新（公告修订），upsert 保证数据幂等性，避免重复入库。

---

## 参考资源

- **Tushare 文档**: https://tushare.pro/document/2
- **SQLAlchemy 文档**: https://docs.sqlalchemy.org/
- **PostgreSQL JSONB**: https://www.postgresql.org/docs/current/datatype-json.html

---

**文档版本**: v1.0  
**最后更新**: 2026-04-02  
**维护者**: AI Assistant
