import type {
  KlineDailyDateListRequest,
  KlineDailyDateListResponse,
} from '@/types/kline';
import { requestJson } from '@/utils/request';

const KLINE_DAILY_PREFIX = '/api/admin/kline/daily';

export function getKlineDailyDateList(
  params: KlineDailyDateListRequest,
): Promise<KlineDailyDateListResponse> {
  return requestJson<KlineDailyDateListResponse>(
    `${KLINE_DAILY_PREFIX}/trade-date-list`,
    {
      method: 'POST',
      body: JSON.stringify(params),
    },
  );
}
