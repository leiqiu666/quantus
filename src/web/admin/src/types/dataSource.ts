export interface ColumnMetric {
  count: number;
  period_stock_count: number;
  ratio: number | null;
  is_complete: boolean;
  has_snapshot: boolean;
  threshold: number;
}

export interface DashboardColumnMeta {
  key: string;
  label: string;
  threshold: number;
  sse_task_key: string;
}

export interface DashboardRow {
  date_key: string;
  period_stock_count: number | null;
  columns: Record<string, ColumnMetric>;
  row_complete: boolean;
}

export interface DashboardMeta {
  group_id: string;
  title: string;
  date_key_type: 'trade_date' | 'report_period' | 'ann_date' | 'month';
  date_label: string;
  columns: DashboardColumnMeta[];
  /** 看板分组对应的 ETL 默认起点（来自后端 settings / .env） */
  default_start: string;
  /** 默认终点（通常为今天或本月） */
  default_end: string;
}

export interface DashboardRequest {
  group_id: string;
  start?: string;
  end?: string;
  page?: number;
  count?: number;
}

export interface DashboardResponse {
  items: DashboardRow[];
  total: number;
  meta: DashboardMeta;
}

export interface DashboardGroupInfo {
  group_id: string;
  title: string;
  date_key_type: string;
}

export interface OverviewWorstColumn {
  key: string;
  label: string;
  ratio: number;
}

export interface OverviewGroupItem {
  group_id: string;
  title: string;
  date_label: string;
  date_key_type: string;
  column_count: number;
  window_row_count: number;
  rows_complete: number;
  complete_rate: number;
  gap_cell_count: number;
  status: 'healthy' | 'warning' | 'critical';
  worst_column: OverviewWorstColumn | null;
  latest_gap_date_key: string | null;
  detail_path: string;
}

export interface OverviewGapItem {
  group_id: string;
  group_title: string;
  date_key: string;
  date_key_type: string;
  column_key: string;
  column_label: string;
  ratio: number | null;
  threshold: number;
  sse_task_key: string;
}

export interface OverviewActiveStock {
  date_key: string;
  listed_count: number;
  trading_count: number;
}

export interface OverviewKeyPathItem {
  name: string;
  latest_date: string | null;
  reference_date: string | null;
  lag_days: number | null;
  status: 'ok' | 'warning' | 'critical' | 'unknown';
}

export interface OverviewSchedulerRunItem {
  run_id: number;
  job_key?: string | null;
  triggered_by: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface OverviewSchedulerSummary {
  jobs_enabled_count: number;
  last_run_at?: string | null;
  today_run_count: number;
  today_success_count: number;
  recent_runs: OverviewSchedulerRunItem[];
}

export interface OverviewResponse {
  as_of: string;
  latest_trade_date: string | null;
  is_trading_day: boolean;
  window: number;
  source_total: number;
  group_total: number;
  groups_healthy: number;
  gap_cell_count: number;
  active_stock: OverviewActiveStock | null;
  groups: OverviewGroupItem[];
  gaps: OverviewGapItem[];
  key_paths: OverviewKeyPathItem[];
  scheduler: OverviewSchedulerSummary;
}

export interface EtlSseRunRequest {
  task_key: string;
  start_date: string;
  end_date?: string;
}
