import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  appendTaskLog,
  closeTask,
  finishRowSequenceTask,
  minimizeTask,
  promoteTaskFromQueue,
  restoreTask,
  setTaskError,
  setTaskFlash,
  setTaskSuccess,
} from '@/store/slices/sseTaskSlice';
import type { AppDispatch } from '@/store';
import type { SseTask } from '@/store/slices/sseTaskSlice';
import { store } from '@/store';
import { ETL_SSE_MAX_CONCURRENT } from '@/config/sse';
import { cancelSchedulerRun } from '@/services/scheduler';
import { executeEtlSseStream } from './sseRunner';
import { useTaskFlashLifecycle } from './useTaskFlashLifecycle';
import SseTaskModal from './SseTaskModal';
import SseTaskDock from './SseTaskDock';

const runningRef = new Set<string>();
const abortControllers = new Map<string, AbortController>();

function tryStartQueuedTasks(dispatch: AppDispatch) {
  const tasks = store.getState().sseTask.tasks;
  const queued = tasks.filter(
    (t) => t.status === 'queued' && !runningRef.has(t.id),
  );
  for (const task of queued) {
    if (runningRef.size >= ETL_SSE_MAX_CONCURRENT) {
      break;
    }
    startSseTask(task, dispatch);
  }
}

async function runRowSequenceTask(task: SseTask, dispatch: AppDispatch) {
  const steps = task.steps ?? [];
  const controller = new AbortController();
  abortControllers.set(task.id, controller);

  try {
    await executeEtlSseStream({
      taskId: task.id,
      dispatch,
      signal: controller.signal,
      mode: 'row_sequence',
      taskKey: 'row_sequence',
      name: task.name,
      startDate: task.startDate,
      endDate: task.endDate,
      dashboardGroupId: task.dashboardGroupId,
      dashboardDateKey: task.dashboardDateKey,
      steps,
    });

    if (controller.signal.aborted) {
      return;
    }

    const latest = store.getState().sseTask.tasks.find((t) => t.id === task.id);
    const failedCount = latest?.failedStepCount ?? 0;
    dispatch(
      finishRowSequenceTask({
        id: task.id,
        failedCount,
        totalSteps: steps.length,
      }),
    );
    dispatch(
      setTaskFlash({
        id: task.id,
        flash: failedCount > 0 ? 'error' : 'success',
      }),
    );
  } catch (err: unknown) {
    if (controller.signal.aborted) {
      dispatch(appendTaskLog({ id: task.id, message: '任务已停止' }));
      return;
    }
    const message = err instanceof Error ? err.message : String(err);
    if (message === '任务已停止') {
      return;
    }
    const latestAfterError = store
      .getState()
      .sseTask.tasks.find((t) => t.id === task.id);
    const failedAfterError = latestAfterError?.failedStepCount ?? 0;
    if (failedAfterError > 0) {
      dispatch(
        finishRowSequenceTask({
          id: task.id,
          failedCount: failedAfterError,
          totalSteps: steps.length,
        }),
      );
      dispatch(setTaskFlash({ id: task.id, flash: 'error' }));
      return;
    }
    dispatch(setTaskError({ id: task.id, message }));
    dispatch(setTaskFlash({ id: task.id, flash: 'error' }));
  } finally {
    runningRef.delete(task.id);
    abortControllers.delete(task.id);
    tryStartQueuedTasks(dispatch);
  }
}

async function runSingleSseTask(task: SseTask, dispatch: AppDispatch) {
  const controller = new AbortController();
  abortControllers.set(task.id, controller);

  dispatch(appendTaskLog({ id: task.id, message: '开始连接…' }));

  try {
    await executeEtlSseStream({
      taskId: task.id,
      dispatch,
      signal: controller.signal,
      mode: task.mode,
      taskKey: task.taskKey,
      jobKey: task.jobKey,
      startDate: task.startDate,
      endDate: task.endDate,
      backtest: task.backtest,
    });
    dispatch(setTaskSuccess({ id: task.id }));
    dispatch(setTaskFlash({ id: task.id, flash: 'success' }));
  } catch (err: unknown) {
    if (controller.signal.aborted) {
      dispatch(appendTaskLog({ id: task.id, message: '任务已停止' }));
      return;
    }
    const message = err instanceof Error ? err.message : String(err);
    if (message === '任务已停止') {
      return;
    }
    dispatch(setTaskError({ id: task.id, message }));
    dispatch(setTaskFlash({ id: task.id, flash: 'error' }));
  } finally {
    runningRef.delete(task.id);
    abortControllers.delete(task.id);
    tryStartQueuedTasks(dispatch);
  }
}

function startSseTask(task: SseTask, dispatch: AppDispatch) {
  if (runningRef.has(task.id)) {
    return;
  }
  runningRef.add(task.id);
  dispatch(promoteTaskFromQueue(task.id));

  if (task.mode === 'row_sequence') {
    void runRowSequenceTask(task, dispatch);
    return;
  }

  void runSingleSseTask(task, dispatch);
}

export default function SseTaskManager() {
  const dispatch = useAppDispatch();
  const tasks = useAppSelector((s) => s.sseTask.tasks);

  const expandedTask = tasks.find((t) => t.expanded) ?? null;

  const drainQueue = useCallback(() => {
    tryStartQueuedTasks(dispatch);
  }, [dispatch]);

  useEffect(() => {
    drainQueue();
  }, [tasks, drainQueue]);

  const handleClose = useCallback(
    (id: string) => {
      // 仅关闭 UI / 断开 SSE 订阅，不取消后端补位（关页不中断）
      runningRef.delete(id);
      abortControllers.get(id)?.abort();
      abortControllers.delete(id);
      dispatch(closeTask(id));
      tryStartQueuedTasks(dispatch);
    },
    [dispatch],
  );

  const handleStop = useCallback(
    async (id: string) => {
      const task = store.getState().sseTask.tasks.find((t) => t.id === id);
      if (task?.runId != null) {
        try {
          await cancelSchedulerRun(task.runId);
        } catch {
          // 仍 abort 前端订阅；后端可能已结束
        }
      }
      abortControllers.get(id)?.abort();
      dispatch(appendTaskLog({ id, message: '已请求停止（当前日/期结束后生效）' }));
    },
    [dispatch],
  );

  useTaskFlashLifecycle(tasks, handleClose);

  return (
    <>
      <SseTaskModal
        task={expandedTask}
        allTasks={tasks}
        open={expandedTask !== null && !expandedTask.minimized}
        onMinimize={() => {
          if (expandedTask) {
            dispatch(minimizeTask(expandedTask.id));
          }
        }}
        onClose={() => {
          if (expandedTask) {
            handleClose(expandedTask.id);
          }
        }}
        onStop={() => {
          if (expandedTask) {
            void handleStop(expandedTask.id);
          }
        }}
      />
      <SseTaskDock
        tasks={tasks}
        onRestore={(id) => dispatch(restoreTask(id))}
        onClose={handleClose}
        onStop={(id) => {
          void handleStop(id);
        }}
      />
    </>
  );
}
