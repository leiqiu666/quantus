export interface FactorMetaItem {
  factor_name: string;
  display_name: string | null;
  source: string;
  category: string | null;
  formula: string | null;
  start_date: string | null;
  end_date: string | null;
  month_count: number | null;
}

export interface FactorComboItem {
  factor_name: string;
  weight: number;
}

export interface FactorCombo {
  id: number;
  name: string;
  items: FactorComboItem[];
  remark: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NavPoint {
  trade_date: string;
  value: number;
}

export interface BacktestRunItem {
  run_id: string;
  backtest_mode: string;
  factor_name: string | null;
  combo_id: number | null;
  combo_name: string | null;
  start_date: string;
  end_date: string;
  rebalance: string;
  groups: number;
  status: string;
  ic_mean: number | null;
  rank_ic_mean: number | null;
  sharpe: number | null;
  annual_return: number | null;
  mdd: number | null;
  output_dir: string | null;
  error_message: string | null;
  created_at: string | null;
  summary?: Record<string, unknown>;
  returns?: Record<string, unknown>[];
  ic?: { trade_date: string; ic: number | null; rank_ic: number | null }[];
  nav_curves?: {
    long_short?: NavPoint[];
    top?: NavPoint[];
    bottom?: NavPoint[];
    benchmark?: NavPoint[];
    excess?: NavPoint[];
  };
  group_totals?: {
    group_id: string;
    total_return: number;
    final_nav: number;
  }[];
  turnover_series?: { trade_date: string; turnover: number }[];
  yearly?: {
    year: string;
    annual_return: number | null;
    sharpe: number | null;
    mdd: number | null;
    n_days: number;
  }[];
  warnings?: string[];
  cost?: {
    commission_rate?: number;
    stamp_duty_rate?: number;
    slippage_rate?: number;
  };
  benchmark?: string | null;
}

export interface BacktestTableResponse {
  name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
}

export interface FactorCsResponse {
  trade_date: string;
  factor_name: string;
  rows: { ts_code: string; value: number; rank: number }[];
  quantiles: {
    p10?: number | null;
    p50?: number | null;
    p90?: number | null;
    count?: number;
  };
}

export interface StockKlineResponse {
  ts_code: string;
  start: string;
  end: string;
  bars: Record<string, unknown>[];
  factor: { trade_date: string; value: number }[];
  factor_name: string | null;
}

export interface QuoteResponse {
  mode: string;
  ts_code: string;
  trade_date: string | null;
  price: number | null;
  pre_close: number | null;
  change_pct: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  vol: number | null;
  message: string | null;
}
