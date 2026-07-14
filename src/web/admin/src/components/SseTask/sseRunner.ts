import type { AppDispatch } from '@/store';
import { store } from '@/store';
import {
  appendTaskLog,
  completeSequenceStep,
  failSequenceStep,
  setTaskRunId,
  setTaskRunning,
  setTaskTotal,
  updateScheduleCommandProgress,
  updateTaskProgress,
} from '@/store/slices/sseTaskSlice';
import type { SseTaskMode, SseTaskStep } from '@/store/slices/sseTaskSlice';
import { FINANCIAL_SSE_ENDPOINTS } from '@/services/financial';
import { ETL_SSE_RUN_SEQUENCE_URL, ETL_SSE_RUN_URL } from '@/services/etlSse';
import { buildSchedulerJobRunUrl } from '@/services/scheduler';
import { consumeSsePost } from '@/utils/sse-client';

const REPORT_HISTORY_URL: Record<string, string> = {
  report_income_history_init: FINANCIAL_SSE_ENDPOINTS.income,
  report_balance_history_init: FINANCIAL_SSE_ENDPOINTS.balance,
  report_cashflow_history_init: FINANCIAL_SSE_ENDPOINTS.cashflow,
  report_indicator_history_init: FINANCIAL_SSE_ENDPOINTS.indicator,
};

export interface EtlSseRunParams {
  mode: SseTaskMode;
  taskKey: string;
  jobKey?: string;
  startDate: string;
  endDate?: string;
  name?: string;
  dashboardGroupId?: string;
  dashboardDateKey?: string;
  steps?: SseTaskStep[];
  backtest?: {
    backtestMode: 'single' | 'combo';
    factorName?: string;
    comboId?: number;
    groups?: number;
    rebalance?: string;
    commissionRate?: number;
    stampDutyRate?: number;
    slippageRate?: number;
  };
}

export interface ExecuteEtlSseOptions extends EtlSseRunParams {
  taskId: string;
  dispatch: AppDispatch;
  signal: AbortSignal;
  /** 行级顺序任务：子步骤进度只写日志，不更新总进度条（legacy；后端串行后少用） */
  logSubProgressOnly?: boolean;
}

function resolveUrl(mode: SseTaskMode, taskKey: string, jobKey?: string): string {
  if (mode === 'schedule_job') {
    return buildSchedulerJobRunUrl(jobKey ?? taskKey);
  }
  if (mode === 'row_sequence') {
    return ETL_SSE_RUN_SEQUENCE_URL;
  }
  if (mode === 'report_history') {
    return REPORT_HISTORY_URL[taskKey];
  }
  return ETL_SSE_RUN_URL;
}

function resolveBody(params: EtlSseRunParams): Record<string, unknown> {
  if (params.mode === 'schedule_job') {
    return {};
  }
  if (params.mode === 'row_sequence') {
    return {
      name: params.name,
      dashboard_group_id: params.dashboardGroupId,
      dashboard_date_key: params.dashboardDateKey,
      steps: (params.steps ?? []).map((s) => ({
        task_key: s.taskKey,
        label: s.label,
        start_date: s.startDate,
        end_date: s.endDate ?? s.startDate,
        column_key: s.columnKey,
        threshold: s.threshold,
      })),
    };
  }
  if (params.mode === 'report_history') {
    return { start_date: params.startDate };
  }
  const body: Record<string, unknown> = {
    task_key: params.taskKey,
    start_date: params.startDate,
    end_date: params.endDate ?? params.startDate,
  };
  if (params.taskKey === 'backtest_run' && params.backtest) {
    body.backtest_mode = params.backtest.backtestMode;
    if (params.backtest.factorName) {
      body.factor_name = params.backtest.factorName;
    }
    if (params.backtest.comboId != null) {
      body.combo_id = params.backtest.comboId;
    }
    if (params.backtest.groups != null) {
      body.groups = params.backtest.groups;
    }
    if (params.backtest.rebalance) {
      body.rebalance = params.backtest.rebalance;
    }
    if (params.backtest.commissionRate != null) {
      body.commission_rate = params.backtest.commissionRate;
    }
    if (params.backtest.stampDutyRate != null) {
      body.stamp_duty_rate = params.backtest.stampDutyRate;
    }
    if (params.backtest.slippageRate != null) {
      body.slippage_rate = params.backtest.slippageRate;
    }
  }
  return body;
}

export function executeEtlSseStream(options: ExecuteEtlSseOptions): Promise<void> {
  const {
    taskId,
    dispatch,
    signal,
    logSubProgressOnly = false,
    ...params
  } = options;

  return new Promise((resolve, reject) => {
    let settled = false;

    const finish = (fn: () => void) => {
      if (settled) {
        return;
      }
      settled = true;
      fn();
    };

    consumeSsePost(
      resolveUrl(params.mode, params.taskKey, params.jobKey),
      resolveBody(params),
      (event) => {
        if ('error' in event && typeof event.error === 'string') {
          finish(() => reject(new Error(event.error)));
          return;
        }
        if (typeof event.run_id === 'number') {
          dispatch(setTaskRunId({ id: taskId, runId: event.run_id }));
          dispatch(
            appendTaskLog({
              id: taskId,
              message: `执行记录 #${event.run_id}`,
            }),
          );
        }
        if (event.status === 'started') {
          dispatch(setTaskRunning(taskId));
          dispatch(appendTaskLog({ id: taskId, message: '连接已建立' }));
          return;
        }
        if (typeof event.log === 'string') {
          if (
            params.mode === 'row_sequence' &&
            event.log.startsWith('错误 · ')
          ) {
            const m = event.log.match(/^错误 · (.+)：([\s\S]+)$/);
            if (m) {
              const stepIndex =
                store.getState().sseTask.tasks.find((t) => t.id === taskId)
                  ?.sequenceStepIndex ?? 0;
              dispatch(
                failSequenceStep({
                  id: taskId,
                  stepIndex,
                  label: m[1],
                  message: m[2],
                }),
              );
              return;
            }
          }
          dispatch(appendTaskLog({ id: taskId, message: event.log }));
          return;
        }
        if (event.status === 'running' && typeof event.total === 'number') {
          if (!logSubProgressOnly) {
            dispatch(setTaskTotal({ id: taskId, total: event.total }));
          }
          const msg =
            params.mode === 'schedule_job'
              ? `共 ${event.total} 条命令待执行`
              : params.mode === 'row_sequence'
                ? `共 ${event.total} 列待补位`
                : `共 ${event.total} 步待处理`;
          dispatch(appendTaskLog({ id: taskId, message: msg }));
          return;
        }
        if (
          (params.mode === 'schedule_job' || params.mode === 'row_sequence') &&
          typeof event.cmd_index === 'number' &&
          typeof event.cmd_total === 'number' &&
          typeof event.cmd_label === 'string' &&
          typeof event.cmd_pct === 'number'
        ) {
          dispatch(
            updateScheduleCommandProgress({
              id: taskId,
              cmdIndex: event.cmd_index,
              cmdTotal: event.cmd_total,
              cmdLabel: event.cmd_label,
              cmdPct: event.cmd_pct,
            }),
          );
          return;
        }
        if (
          typeof event.index === 'number' &&
          typeof event.total === 'number' &&
          typeof event.period === 'string' &&
          typeof event.saved === 'number'
        ) {
          const saved = event.saved;
          if (params.mode === 'row_sequence') {
            dispatch(
              completeSequenceStep({
                id: taskId,
                stepIndex: event.index - 1,
                message:
                  saved > 0
                    ? `第 ${event.index}/${event.total} 步 ${event.period}，写入 ${saved} 条`
                    : `${event.period} 完成`,
              }),
            );
            return;
          }
          const logMessage =
            params.mode === 'schedule_job'
              ? saved > 0
                ? `第 ${event.index}/${event.total} 步 ${event.period}，写入 ${saved} 条`
                : `第 ${event.index}/${event.total} 步 ${event.period}，完成`
              : saved > 0
                ? `第 ${event.index}/${event.total} 步 ${event.period}，写入 ${saved} 条`
                : `第 ${event.index}/${event.total} 步 ${event.period}，完成`;
          if (logSubProgressOnly) {
            dispatch(appendTaskLog({ id: taskId, message: logMessage }));
          } else {
            dispatch(
              updateTaskProgress({
                id: taskId,
                index: event.index,
                total: event.total,
                period: event.period,
                saved,
                logMessage,
              }),
            );
          }
          return;
        }
        if (event.done === true) {
          if (event.status === 'cancelled') {
            const msg =
              typeof event.message === 'string' ? event.message : '任务已停止';
            dispatch(appendTaskLog({ id: taskId, message: msg }));
            finish(() => reject(new Error('任务已停止')));
            return;
          }
          const msg =
            typeof event.message === 'string'
              ? event.message
              : Array.isArray(event.periods)
                ? `完成，共处理 ${event.periods.length} 个报告期`
                : '任务完成';
          dispatch(appendTaskLog({ id: taskId, message: msg }));
          finish(() => resolve());
        }
      },
      signal,
    ).catch((err: unknown) => {
      if (signal.aborted) {
        finish(() => reject(new Error('任务已取消')));
        return;
      }
      const message = err instanceof Error ? err.message : String(err);
      finish(() => reject(new Error(message)));
    });
  });
}
