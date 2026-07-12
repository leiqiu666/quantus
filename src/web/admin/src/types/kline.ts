export interface KlineDailyDateItem {
  trade_date: string;
  period_stock_count: number;
  kline_daily_count: number;
  kline_adj_factor_count: number;
  kline_stk_limit_count: number;
}

export interface KlineDailyDateListRequest {
  start_date?: string;
  end_date?: string;
  page?: number;
  count?: number;
}

export interface KlineDailyDateListResponse {
  items: KlineDailyDateItem[];
  total: number;
}
