import type { EtlSseRunRequest } from '@/types/dataSource';

export const ETL_SSE_RUN_URL = '/api/admin/etl/sse/run';
export const ETL_SSE_RUN_SEQUENCE_URL = '/api/admin/etl/sse/run-sequence';

export function buildEtlSseBody(params: EtlSseRunRequest): EtlSseRunRequest {
  return params;
}
