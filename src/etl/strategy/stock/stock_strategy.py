from src.etl.workflow.stock.stock_workflow import StockWorkflow
from src.etl.workflow.stock.stock_delist_backfill_workflow import StockDelistBackfillWorkflow


class StockStrategy:
    def __init__(self):
        self.stock_workflow = StockWorkflow()
        self.delist_backfill_workflow = StockDelistBackfillWorkflow()

    def pull_stock_list_a(self):
        return self.stock_workflow.pull_stock_list_a()

    def backfill_delist_date_from_kline(
        self,
        *,
        dry_run: bool = False,
        report_path: str | None = "docs/analysis/delist-date-backfill-from-kline.md",
    ) -> dict[str, int | str]:
        return self.delist_backfill_workflow.backfill_delist_date_from_kline(
            dry_run=dry_run,
            report_path=report_path,
        )
