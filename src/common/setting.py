import sys
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import ChatOpenAI

from src.common.etl_start import resolve_etl_start_date, resolve_etl_start_month


def _default_tdx_quant_enabled() -> bool:
    """非 Windows 开发环境默认不启动本地通达信（客户端仅支持 Win）。"""
    return sys.platform == "win32"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    # openai settings
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_base_model: str = Field(default="", alias="OPENAI_BASE_MODEL")
    # deepseek settings
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="", alias="DEEPSEEK_BASE_URL")
    deepseek_base_model: str = Field(default="", alias="DEEPSEEK_BASE_MODEL")

    # tushare settings
    tushare_api_key: str = Field(default="", alias="TUSHARE_API_KEY")
    tushare_api_url: str = Field(default="http://api.waditu.com/dataapi", alias="TUSHARE_API_URL")
    tushare_channel: str = Field(
        default="official",
        alias="TUSHARE_CHANNEL",
        description="未在 config/tushare_api_channels.json 登记的接口默认渠道；已登记接口以 JSON 为准",
    )
    tushare_ssl_verify: bool = Field(
        default=True,
        alias="TUSHARE_SSL_VERIFY",
        description="是否校验 SSL 证书（第三方镜像自签证书时需关闭）",
    )
    # stocktoday 渠道专属配置
    tushare_stocktoday_api_key: str = Field(
        default="5121045325504027236",
        alias="TUSHARE_STOCKTODAY_API_KEY",
    )
    tushare_stocktoday_api_url: str = Field(
        default="https://tushare.citydata.club/dataapi",
        alias="TUSHARE_STOCKTODAY_API_URL",
    )

    # tdx settings（API 进程本地调用，仅 Windows + 已安装通达信客户端时启用）
    tdx_quant_enabled: bool = Field(
        default_factory=_default_tdx_quant_enabled,
        alias="TDX_QUANT_ENABLED",
    )
    scheduler_enabled: bool = Field(
        default=True,
        alias="SCHEDULER_ENABLED",
        description="API 进程内是否启动 ETL 定时调度（默认 true，仅 API 即可）",
    )
    tdx_root: str = Field(default=r"E:\Program\tdx", alias="TDX_ROOT")
    # 可选：覆盖默认 {TDX_ROOT}/PYPlugins/user 与 TPythClient.dll 路径
    tdx_pyplugins_user_dir: str = Field(default="", alias="TDX_PYPLUGINS_USER")
    tdx_dll_file: str = Field(default="", alias="TDX_DLL_PATH")
    # tdx HTTP 中转（ETL 等远程调用）
    tdx_api_host: str = Field(default="localhost", alias="TDX_API_HOST")
    tdx_api_port: int = Field(default=8000, alias="TDX_API_PORT")
    tdx_api_timeout: int = Field(default=300, alias="TDX_API_TIMEOUT")

    # postgresql settings
    postgresql_user: str = Field(default="", alias="POSTGRESQL_USER")
    postgresql_password: str = Field(default="", alias="POSTGRESQL_PASSWORD")
    postgresql_host: str = Field(default="", alias="POSTGRESQL_HOST")
    postgresql_port: int = Field(default=0, alias="POSTGRESQL_PORT")
    postgresql_database: str = Field(default="", alias="POSTGRESQL_DATABASE")
    postgresql_echo: bool = Field(default=False, alias="POSTGRESQL_ECHO")
    postgresql_pool_size: int = Field(default=10, alias="POSTGRESQL_POOL_SIZE")
    postgresql_max_overflow: int = Field(default=20, alias="POSTGRESQL_MAX_OVERFLOW")

    # business settings — ETL 增量起点见 etl_start_date() / etl_start_month()
    etl_default_start_date: str = Field(default="19901219", alias="ETL_DEFAULT_START_DATE")

    def etl_start_date(self, table: str, *, fallback_table: str | None = None) -> str:
        """DB 表名（snake_case）→ 起始日 YYYYMMDD。env: {TABLE}_START_DATE，空则 ETL_DEFAULT_START_DATE。"""
        return resolve_etl_start_date(
            table, self.etl_default_start_date, fallback_table=fallback_table
        )

    def etl_start_month(self, table: str) -> str:
        """DB 表名 → 起始月 YYYYMM。env: {TABLE}_START_MONTH，空则取 ETL_DEFAULT_START_DATE 前 6 位。"""
        return resolve_etl_start_month(table, self.etl_default_start_date)

    # warehouse settings（PG → Parquet/DuckDB 列存仓库根目录）
    warehouse_root: str = Field(default="./data/warehouse", alias="WAREHOUSE_ROOT")

    # tushare 网络重试（断连时自动重试）
    tushare_retry_interval: int = Field(default=3, alias="TUSHARE_RETRY_INTERVAL", description="重试间隔秒数")
    tushare_retry_max: int = Field(
        default=10000,
        validation_alias=AliasChoices("TUSHARE_RETRY_MAX", "TUSHARE_RETRY_COUNT"),
        description="最大重试次数（.env 可写 TUSHARE_RETRY_COUNT）",
    )
    tushare_timeout: int = Field(default=30, alias="TUSHARE_TIMEOUT", description="Tushare HTTP 超时秒数")

    # 数据源优先级兜底（DB 表为空时使用，逗号分隔）
    kline_daily_sources: str = Field(default="tdx_quant,tushare", alias="KLINE_DAILY_SOURCES")
    kline_daily_by_date_sources: str = Field(default="tushare,tdx_quant", alias="KLINE_DAILY_BY_DATE_SOURCES")
    kline_adj_factor_sources: str = Field(default="tushare", alias="KLINE_ADJ_FACTOR_SOURCES")
    kline_adj_factor_by_date_sources: str = Field(default="tushare", alias="KLINE_ADJ_FACTOR_BY_DATE_SOURCES")
    kline_stk_limit_sources: str = Field(default="tushare", alias="KLINE_STK_LIMIT_SOURCES")
    kline_stk_limit_by_date_sources: str = Field(default="tushare", alias="KLINE_STK_LIMIT_BY_DATE_SOURCES")
    report_income_sources: str = Field(default="tushare", alias="REPORT_INCOME_SOURCES")
    report_balance_sources: str = Field(default="tushare", alias="REPORT_BALANCE_SOURCES")
    report_cashflow_sources: str = Field(default="tushare", alias="REPORT_CASHFLOW_SOURCES")
    report_indicator_sources: str = Field(default="tushare", alias="REPORT_INDICATOR_SOURCES")
    stock_list_sources: str = Field(default="tushare", alias="STOCK_LIST_SOURCES")

    @property
    def postgresql_url(self) -> str:
        """拼接 PostgreSQL 连接 URL"""
        return f"postgresql://{self.postgresql_user}:{self.postgresql_password}@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"

    @property
    def tushare_effective_api_key(self) -> str:
        """根据 TUSHARE_CHANNEL 返回实际使用的 API Key。"""
        if self.tushare_channel.strip().lower() == "stocktoday":
            return self.tushare_stocktoday_api_key
        return self.tushare_api_key

    @property
    def tushare_effective_api_url(self) -> str:
        """根据 TUSHARE_CHANNEL 返回实际使用的 API URL。"""
        if self.tushare_channel.strip().lower() == "stocktoday":
            return self.tushare_stocktoday_api_url
        return self.tushare_api_url

    @property
    def tdx_api_base_url(self) -> str:
        """通达信 HTTP 中转 API 根地址。"""
        return f"http://{self.tdx_api_host}:{self.tdx_api_port}"

    @property
    def tdx_pyplugins_user(self) -> Path:
        """通达信 PYPlugins/user 目录（tqcenter 导入路径）。"""
        if self.tdx_pyplugins_user_dir.strip():
            return Path(self.tdx_pyplugins_user_dir)
        return Path(self.tdx_root) / "PYPlugins" / "user"

    @property
    def tdx_dll_path(self) -> Path:
        """通达信 TPythClient.dll 绝对路径。"""
        if self.tdx_dll_file.strip():
            return Path(self.tdx_dll_file)
        return Path(self.tdx_root) / "PYPlugins" / "TPythClient.dll"

    @property
    def openai_model(self) -> ChatOpenAI:
        return ChatOpenAI(base_url=self.openai_base_url, model=self.openai_base_model, api_key=self.openai_api_key)

settings = Settings()