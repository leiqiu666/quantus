import type { FactorMetaItem } from '@/types/quant';
import { requestJson } from '@/utils/request';

const QUANT_PREFIX = '/api/admin/quant';

export function getFactorList(params?: {
  source?: string;
  category?: string;
}): Promise<FactorMetaItem[]> {
  const query = new URLSearchParams();
  if (params?.source) query.set('source', params.source);
  if (params?.category) query.set('category', params.category);
  const qs = query.toString();
  return requestJson<FactorMetaItem[]>(
    `${QUANT_PREFIX}/factor/list${qs ? `?${qs}` : ''}`,
  );
}
