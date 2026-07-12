import type { SseTask, SseTaskStatus } from '@/store/slices/sseTaskSlice';

export const ETL_TASK_DUPLICATE_MESSAGE =
  '有一个同样的任务已经正在进行中';

export const ROW_SEQUENCE_DUPLICATE_MESSAGE =
  '该日期已有行级补位任务进行中';

const ACTIVE_STATUSES: SseTaskStatus[] = ['queued', 'pending', 'running'];

export function normalizeEtlTaskEndDate(
  startDate: string,
  endDate?: string,
): string {
  return endDate ?? startDate;
}

export function etlTaskMatchKey(
  taskKey: string,
  startDate: string,
  endDate?: string,
): string {
  const end = normalizeEtlTaskEndDate(startDate, endDate);
  return `${taskKey}|${startDate}|${end}`;
}

export function isEtlTaskActive(status: SseTaskStatus): boolean {
  return ACTIVE_STATUSES.includes(status);
}

export function findActiveRowSequence(
  tasks: SseTask[],
  startDate: string,
  endDate?: string,
): SseTask | undefined {
  const end = normalizeEtlTaskEndDate(startDate, endDate);
  return tasks.find(
    (t) =>
      t.mode === 'row_sequence' &&
      isEtlTaskActive(t.status) &&
      t.startDate === startDate &&
      normalizeEtlTaskEndDate(t.startDate, t.endDate) === end,
  );
}

export function findActiveEtlTask(
  tasks: SseTask[],
  taskKey: string,
  startDate: string,
  endDate?: string,
): SseTask | undefined {
  const key = etlTaskMatchKey(taskKey, startDate, endDate);

  const direct = tasks.find(
    (t) =>
      t.mode !== 'schedule_job' &&
      t.mode !== 'row_sequence' &&
      isEtlTaskActive(t.status) &&
      etlTaskMatchKey(t.taskKey, t.startDate, t.endDate) === key,
  );
  if (direct) {
    return direct;
  }

  return tasks.find(
    (t) =>
      t.mode === 'row_sequence' &&
      isEtlTaskActive(t.status) &&
      t.steps?.some(
        (step) =>
          etlTaskMatchKey(step.taskKey, step.startDate, step.endDate) === key,
      ),
  );
}
