import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  appendTaskLog,
  closeTask,
  completeSequenceStep,
  failSequenceStep,
  finishRowSequenceTask,
  minimizeTask,
  promoteTaskFromQueue,
  restoreTask,
  setSequenceStep,
  setTaskError,
  setTaskFlash,
  setTaskSuccess,
} from '@/store/slices/sseTaskSlice';
import type { AppDispatch } from '@/store';
import type { SseTask } from '@/store/slices/sseTaskSlice';
import { store } from '@/store';
import { ETL_SSE_MAX_CONCURRENT } from '@/config/sse';
import { executeEtlSseStream } from './sseRunner';
import { verifyStepCompleteness } from './completenessVerify';
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

  let failedCount = 0;

  try {
    for (let i = 0; i < steps.length; i++) {
      if (controller.signal.aborted) {
        dispatch(appendTaskLog({ id: task.id, message: '任务已取消' }));
        return;
      }

      const step = steps[i];
      dispatch(
        setSequenceStep({
          id: task.id,
          stepIndex: i,
          stepLabel: step.label,
        }),
      );

      try {
        await executeEtlSseStream({
          taskId: task.id,
          dispatch,
          signal: controller.signal,
          logSubProgressOnly: true,
          mode: step.mode,
          taskKey: step.taskKey,
          startDate: step.startDate,
          endDate: step.endDate,
        });

        if (
          task.dashboardGroupId &&
          task.dashboardDateKey &&
          step.columnKey
        ) {
          await verifyStepCompleteness({
            groupId: task.dashboardGroupId,
            dateKey: task.dashboardDateKey,
            columnKey: step.columnKey,
            stepLabel: step.label,
            threshold: step.threshold,
          });
        }

        dispatch(
          completeSequenceStep({
            id: task.id,
            stepIndex: i,
            message: `${step.label} 完成`,
          }),
        );
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          dispatch(appendTaskLog({ id: task.id, message: '任务已取消' }));
          return;
        }
        failedCount += 1;
        const message = err instanceof Error ? err.message : String(err);
        dispatch(
          failSequenceStep({
            id: task.id,
            stepIndex: i,
            label: step.label,
            message,
          }),
        );
      }
    }

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
    });
    dispatch(setTaskSuccess({ id: task.id }));
    dispatch(setTaskFlash({ id: task.id, flash: 'success' }));
  } catch (err: unknown) {
    if (controller.signal.aborted) {
      dispatch(appendTaskLog({ id: task.id, message: '任务已取消' }));
      return;
    }
    const message = err instanceof Error ? err.message : String(err);
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
      runningRef.delete(id);
      abortControllers.get(id)?.abort();
      abortControllers.delete(id);
      dispatch(closeTask(id));
      tryStartQueuedTasks(dispatch);
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
      />
      <SseTaskDock
        tasks={tasks}
        onRestore={(id) => dispatch(restoreTask(id))}
        onClose={handleClose}
      />
    </>
  );
}
