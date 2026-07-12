import { useCallback } from 'react';
import { message } from 'antd';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { store } from '@/store';
import {
  addRowSequenceTask,
  addTask,
  type SseTaskMode,
  type SseTaskStep,
} from '@/store/slices/sseTaskSlice';
import {
  ETL_TASK_DUPLICATE_MESSAGE,
  ROW_SEQUENCE_DUPLICATE_MESSAGE,
  findActiveEtlTask,
  findActiveRowSequence,
} from './etlTaskDedup';

const REPORT_HISTORY_KEYS = new Set([
  'report_income_history_init',
  'report_balance_history_init',
  'report_cashflow_history_init',
  'report_indicator_history_init',
]);

export type EtlTaskParams = {
  taskKey: string;
  label: string;
  startDate: string;
  endDate?: string;
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
};

export type RowSequenceStepParams = EtlTaskParams & {
  columnKey?: string;
  threshold?: number;
};

export type RowSequenceTaskParams = {
  name: string;
  startDate: string;
  endDate?: string;
  dashboardGroupId?: string;
  dashboardDateKey?: string;
  steps: RowSequenceStepParams[];
};

function resolveTaskMode(
  params: Pick<EtlTaskParams, 'taskKey' | 'startDate' | 'endDate'>,
): Exclude<SseTaskMode, 'row_sequence' | 'schedule_job'> {
  return REPORT_HISTORY_KEYS.has(params.taskKey) &&
    (!params.endDate || params.endDate !== params.startDate)
    ? 'report_history'
    : 'etl_generic';
}

function buildTaskPayload(params: EtlTaskParams, id: string) {
  const endPart = params.endDate ? ` ~ ${params.endDate}` : '';
  return {
    id,
    name: `${params.label} · ${params.startDate}${endPart}`,
    mode: resolveTaskMode(params),
    taskKey: params.taskKey,
    startDate: params.startDate,
    endDate: params.endDate,
    backtest: params.backtest,
  };
}

function buildSequenceSteps(steps: RowSequenceStepParams[]): SseTaskStep[] {
  return steps.map((step) => ({
    taskKey: step.taskKey,
    label: step.label,
    startDate: step.startDate,
    endDate: step.endDate,
    columnKey: step.columnKey,
    threshold: step.threshold,
    mode: resolveTaskMode(step),
  }));
}

export function useSseTask() {
  const dispatch = useAppDispatch();
  const tasks = useAppSelector((s) => s.sseTask.tasks);

  const isEtlTaskDuplicate = useCallback(
    (
      params: Pick<
        EtlTaskParams,
        'taskKey' | 'startDate' | 'endDate' | 'backtest'
      >,
    ) =>
      findActiveEtlTask(
        store.getState().sseTask.tasks,
        params.taskKey,
        params.startDate,
        params.endDate,
        params.backtest,
      ) !== undefined,
    [tasks],
  );

  const guardEtlTask = useCallback(
    (
      params: Pick<
        EtlTaskParams,
        'taskKey' | 'startDate' | 'endDate' | 'backtest'
      >,
    ): boolean => {
      if (isEtlTaskDuplicate(params)) {
        message.warning(ETL_TASK_DUPLICATE_MESSAGE);
        return false;
      }
      return true;
    },
    [isEtlTaskDuplicate],
  );

  const startEtlTask = useCallback(
    (
      params: EtlTaskParams,
      options?: { silent?: boolean },
    ): boolean => {
      if (isEtlTaskDuplicate(params)) {
        if (!options?.silent) {
          message.warning(ETL_TASK_DUPLICATE_MESSAGE);
        }
        return false;
      }

      dispatch(addTask(buildTaskPayload(params, crypto.randomUUID())));
      return true;
    },
    [dispatch, isEtlTaskDuplicate],
  );

  const startRowSequenceTask = useCallback(
    (
      params: RowSequenceTaskParams,
      options?: { silent?: boolean },
    ): boolean => {
      const activeTasks = store.getState().sseTask.tasks;
      if (
        findActiveRowSequence(
          activeTasks,
          params.startDate,
          params.endDate,
        )
      ) {
        if (!options?.silent) {
          message.warning(ROW_SEQUENCE_DUPLICATE_MESSAGE);
        }
        return false;
      }

      const pendingSteps = params.steps.filter(
        (step) =>
          findActiveEtlTask(
            activeTasks,
            step.taskKey,
            step.startDate,
            step.endDate,
          ) === undefined,
      );
      if (pendingSteps.length === 0) {
        if (!options?.silent) {
          message.warning(ETL_TASK_DUPLICATE_MESSAGE);
        }
        return false;
      }

      dispatch(
        addRowSequenceTask({
          id: crypto.randomUUID(),
          name: params.name,
          startDate: params.startDate,
          endDate: params.endDate,
          dashboardGroupId: params.dashboardGroupId,
          dashboardDateKey: params.dashboardDateKey,
          steps: buildSequenceSteps(pendingSteps),
        }),
      );
      return true;
    },
    [dispatch],
  );

  const startScheduleJob = useCallback(
    (params: { jobKey: string; name: string }) => {
      dispatch(
        addTask({
          id: crypto.randomUUID(),
          name: params.name,
          mode: 'schedule_job',
          taskKey: params.jobKey,
          jobKey: params.jobKey,
          startDate: '',
        }),
      );
    },
    [dispatch],
  );

  return {
    startEtlTask,
    startRowSequenceTask,
    guardEtlTask,
    isEtlTaskDuplicate,
    startScheduleJob,
  };
}
