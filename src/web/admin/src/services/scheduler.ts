import type {
  ScheduleCommandItem,
  ScheduleJobCreateRequest,
  ScheduleJobItem,
  ScheduleJobUpdateRequest,
  ScheduleOverviewResponse,
  ScheduleRunItem,
  ScheduleRunListResponse,
} from '@/types/scheduler';
import { requestJson } from '@/utils/request';

const PREFIX = '/api/admin/scheduler';

export function buildSchedulerJobRunUrl(jobKey: string): string {
  return `${PREFIX}/jobs/${encodeURIComponent(jobKey)}/run`;
}

export function getSchedulerCommands(): Promise<ScheduleCommandItem[]> {
  return requestJson<ScheduleCommandItem[]>(`${PREFIX}/commands`);
}

export function getSchedulerOverview(): Promise<ScheduleOverviewResponse> {
  return requestJson<ScheduleOverviewResponse>(`${PREFIX}/overview`);
}

export function getSchedulerJobs(): Promise<ScheduleJobItem[]> {
  return requestJson<ScheduleJobItem[]>(`${PREFIX}/jobs`);
}

export function getSchedulerJob(jobKey: string): Promise<ScheduleJobItem> {
  return requestJson<ScheduleJobItem>(`${PREFIX}/jobs/${encodeURIComponent(jobKey)}`);
}

export function createSchedulerJob(body: ScheduleJobCreateRequest): Promise<ScheduleJobItem> {
  return requestJson<ScheduleJobItem>(`${PREFIX}/jobs`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function updateSchedulerJob(
  jobKey: string,
  body: ScheduleJobUpdateRequest,
): Promise<ScheduleJobItem> {
  return requestJson<ScheduleJobItem>(`${PREFIX}/jobs/${encodeURIComponent(jobKey)}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function deleteSchedulerJob(jobKey: string): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(`${PREFIX}/jobs/${encodeURIComponent(jobKey)}`, {
    method: 'DELETE',
  });
}

export function listSchedulerRuns(params?: {
  job_key?: string;
  page?: number;
  count?: number;
}): Promise<ScheduleRunListResponse> {
  return requestJson<ScheduleRunListResponse>(`${PREFIX}/runs`, {
    method: 'POST',
    body: JSON.stringify({
      job_key: params?.job_key,
      page: params?.page ?? 1,
      count: params?.count ?? 20,
    }),
  });
}

export function getSchedulerRun(runId: number): Promise<ScheduleRunItem> {
  return requestJson<ScheduleRunItem>(`${PREFIX}/runs/${runId}`);
}
