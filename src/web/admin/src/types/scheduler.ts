export type ScheduleHint = 'morning' | 'pre_open' | 'post_close' | 'anytime';
export type ScheduleKind = 'daily_at' | 'weekdays_at' | 'cron';

export interface ScheduleCommandItem {
  command_key: string;
  label: string;
  typer_group: string;
  typer_command: string;
  category: string;
  schedule_hint: ScheduleHint;
  run_on_trading_day: boolean;
  referenced_by: string[];
  is_referenced: boolean;
}

export interface ScheduleJobItem {
  job_key: string;
  name: string;
  schedule_kind: ScheduleKind;
  schedule_time: string;
  cron_expr?: string | null;
  run_on_trading_day: boolean;
  enabled: boolean;
  command_keys: string[];
  command_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ScheduleRunStepItem {
  step_id: number;
  command_key: string;
  sort_order: number;
  status: string;
  saved_count?: number | null;
  message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ScheduleRunItem {
  run_id: number;
  job_id?: number | null;
  job_key?: string | null;
  triggered_by: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
  steps?: ScheduleRunStepItem[];
}

export interface ScheduleOverviewResponse {
  command_total: number;
  command_referenced_count: number;
  command_unreferenced_count: number;
  commands: ScheduleCommandItem[];
  jobs_enabled_count: number;
  last_run_at?: string | null;
  recent_runs: ScheduleRunItem[];
}

export interface ScheduleJobCreateRequest {
  job_key: string;
  name: string;
  schedule_kind: ScheduleKind;
  schedule_time: string;
  cron_expr?: string | null;
  run_on_trading_day?: boolean;
  enabled?: boolean;
  command_keys: string[];
}

export interface ScheduleJobUpdateRequest {
  name?: string;
  schedule_kind?: ScheduleKind;
  schedule_time?: string;
  cron_expr?: string | null;
  run_on_trading_day?: boolean;
  enabled?: boolean;
  command_keys?: string[];
}

export interface ScheduleRunListResponse {
  items: ScheduleRunItem[];
  total: number;
}

export interface ScheduleRunTriggerResponse {
  run_id: number;
}

export const SCHEDULE_PRESETS: { label: string; kind: ScheduleKind; time: string }[] = [
  { label: '每天早上 06:00', kind: 'daily_at', time: '06:00' },
  { label: '开盘前 09:25', kind: 'weekdays_at', time: '09:25' },
  { label: '收盘后 16:30', kind: 'weekdays_at', time: '16:30' },
  { label: '夜间低峰 02:00', kind: 'daily_at', time: '02:00' },
];

export const scheduleHintLabels: Record<ScheduleHint, string> = {
  morning: '早晨',
  pre_open: '开盘前',
  post_close: '收盘后',
  anytime: '任意时间',
};

export const scheduleKindLabels: Record<ScheduleKind, string> = {
  daily_at: '每天',
  weekdays_at: '工作日',
  cron: 'Cron',
};

export const scheduleRunStatusLabels: Record<string, string> = {
  running: '运行中',
  success: '成功',
  failed: '失败',
  partial: '部分成功',
  skipped: '已跳过',
};

export function formatScheduleRunStatus(status: string): string {
  return scheduleRunStatusLabels[status] ?? status;
}
