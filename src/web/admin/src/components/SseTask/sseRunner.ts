import type { AppDispatch } from '@/store';
import {
  appendTaskLog,
  setTaskError,
  setTaskRunning,
  setTaskTotal,
  updateTaskProgress,
} from '@/store/slices/sseTaskSlice';
import type { SseTaskMode } from '@/store/slices/sseTaskSlice';
import { FINANCIAL_SSE_ENDPOINTS } from '@/services/financial';
import { ETL_SSE_RUN_URL } from '@/services/etlSse';
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
}

export interface ExecuteEtlSseOptions extends EtlSseRunParams {
  taskId: string;
  dispatch: AppDispatch;
  signal: AbortSignal;
  /** 行级顺序任务：子步骤进度只写日志，不更新总进度条 */
  logSubProgressOnly?: boolean;
}

function resolveUrl(mode: SseTaskMode, taskKey: string, jobKey?: string): string {
  if (mode === 'schedule_job') {
    return buildSchedulerJobRunUrl(jobKey ?? taskKey);
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
  if (params.mode === 'report_history') {
    return { start_date: params.startDate };
  }
  return {
    task_key: params.taskKey,
    start_date: params.startDate,
    end_date: params.endDate ?? params.startDate,
  };
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
        if (event.status === 'started') {
          dispatch(setTaskRunning(taskId));
          dispatch(appendTaskLog({ id: taskId, message: '连接已建立' }));
          return;
        }
        if (typeof event.log === 'string') {
          dispatch(appendTaskLog({ id: taskId, message: event.log }));
          return;
        }
        if (event.status === 'running' && typeof event.total === 'number') {
          if (!logSubProgressOnly) {
            dispatch(setTaskTotal({ id: taskId, total: event.total }));
          }
          dispatch(
            appendTaskLog({
              id: taskId,
              message:
                params.mode === 'schedule_job'
                  ? `共 ${event.total} 条命令待执行`
                  : `共 ${event.total} 步待处理`,
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
