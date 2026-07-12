# Quantus

# src 目录结构
- model 数据库模型
- client 第三方数据库客户端，用于封装从tushare sina等平台获取数据的原子层，将数据按照model 加工，例如：pull_report_income，调用了income_vip
- service 封装具体业务逻辑，例如：collect_report_income，掉用 pull_report_income 加工json，并保存数据库。
- collect 例如 调用 collect_report_income ，传入不同参数，完成各种维度的数据更新和下载


# API启动
-  uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Linux 开发无通达信客户端时，在 `.env` 设置 `TDX_QUANT_ENABLED=false`（非 Windows 默认即为 false）。Windows 上启用需配置 `TDX_ROOT`，可选 `TDX_PYPLUGINS_USER`、`TDX_DLL_PATH` 覆盖路径。




从 get_tushare_doc 本地文档重新生成 JSON
uv run python scripts/generate_tushare_channel_config.py
