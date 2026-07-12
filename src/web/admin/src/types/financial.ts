export interface ReportPeriodItem {
  report_period: string;
  period_stock_count: number;
  report_income_count: number;
  report_balance_count: number;
  report_cashflow_count: number;
}

export interface ReportPeriodListRequest {
  start_period_date?: string;
  end_period_date?: string;
  page?: number;
  count?: number;
}

export type FinancialReportTaskType =
  | 'income'
  | 'balance'
  | 'cashflow'
  | 'indicator';

export interface IncomeHistoryInitRequest {
  start_date?: string;
}

export interface SseStartedEvent {
  status: 'started';
}

export interface SseRunningEvent {
  status: 'running';
  total: number;
}

export interface SseProgressEvent {
  index: number;
  total: number;
  period: string;
  saved: number;
}

export interface SseFinalEvent {
  done: true;
  periods: string[];
}

export interface SseErrorEvent {
  error: string;
}

export type SseFinancialEvent =
  | SseStartedEvent
  | SseRunningEvent
  | SseProgressEvent
  | SseFinalEvent
  | SseErrorEvent;
