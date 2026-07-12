import type {
  DashboardGroupInfo,
  DashboardRequest,
  DashboardResponse,
  OverviewResponse,
} from '@/types/dataSource';
import { requestJson } from '@/utils/request';

const PREFIX = '/api/admin/data-source';

export function listDashboardGroups(): Promise<DashboardGroupInfo[]> {
  return requestJson<DashboardGroupInfo[]>(`${PREFIX}/groups`);
}

export function getOverview(window = 5): Promise<OverviewResponse> {
  return requestJson<OverviewResponse>(`${PREFIX}/overview?window=${window}`);
}

export function getDashboard(
  params: DashboardRequest,
): Promise<DashboardResponse> {
  return requestJson<DashboardResponse>(`${PREFIX}/dashboard`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
