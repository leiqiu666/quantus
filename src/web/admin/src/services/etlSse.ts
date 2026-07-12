import type { EtlSseRunRequest } from '@/types/dataSource';

export const ETL_SSE_RUN_URL = '/api/admin/etl/sse/run';

export function buildEtlSseBody(params: EtlSseRunRequest): EtlSseRunRequest {
  return params;
}
