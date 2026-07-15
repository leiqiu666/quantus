import type {
  BacktestRunItem,
  BacktestTableResponse,
  FactorCombo,
  FactorComboItem,
  FactorMetaItem,
  FactorMetaListResponse,
  FeatureMetaItem,
  FeatureMetaListResponse,
} from '@/types/quant';
import { requestJson } from '@/utils/request';

const QUANT_PREFIX = '/api/admin/quant';

export function getFactorList(params?: {
  page?: number;
  page_size?: number;
  source?: string;
  category?: string;
  keyword?: string;
}): Promise<FactorMetaListResponse> {
  const query = new URLSearchParams();
  query.set('page', String(params?.page ?? 1));
  query.set('page_size', String(params?.page_size ?? 20));
  if (params?.source) query.set('source', params.source);
  if (params?.category) query.set('category', params.category);
  if (params?.keyword) query.set('keyword', params.keyword);
  return requestJson<FactorMetaListResponse>(
    `${QUANT_PREFIX}/factor/list?${query}`,
  );
}

/** 下拉选项：一次拉较全量（≤500） */
export async function getFactorOptions(): Promise<FactorMetaItem[]> {
  const res = await getFactorList({ page: 1, page_size: 500 });
  return res.items;
}

export function getFactorDetail(factorName: string): Promise<FactorMetaItem> {
  return requestJson<FactorMetaItem>(
    `${QUANT_PREFIX}/factor/${encodeURIComponent(factorName)}`,
  );
}

export function updateFactorMeta(
  factorName: string,
  body: {
    display_name?: string | null;
    category?: string | null;
    formula?: string | null;
  },
): Promise<FactorMetaItem> {
  return requestJson<FactorMetaItem>(
    `${QUANT_PREFIX}/factor/${encodeURIComponent(factorName)}`,
    { method: 'PUT', body: JSON.stringify(body) },
  );
}

export function getFactorSource(factorName: string): Promise<{
  factor_name: string;
  python_path: string;
  content: string;
}> {
  return requestJson(
    `${QUANT_PREFIX}/factor/${encodeURIComponent(factorName)}/source`,
  );
}

export function getFeatureList(params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  feature_kind?: string;
  source_kind?: string;
  enabled?: number;
}): Promise<FeatureMetaListResponse> {
  const query = new URLSearchParams();
  query.set('page', String(params?.page ?? 1));
  query.set('page_size', String(params?.page_size ?? 20));
  if (params?.keyword) query.set('keyword', params.keyword);
  if (params?.feature_kind) query.set('feature_kind', params.feature_kind);
  if (params?.source_kind) query.set('source_kind', params.source_kind);
  if (params?.enabled != null) query.set('enabled', String(params.enabled));
  return requestJson<FeatureMetaListResponse>(
    `${QUANT_PREFIX}/feature/list?${query}`,
  );
}

export function seedFeatures(): Promise<{ upserted: number }> {
  return requestJson<{ upserted: number }>(`${QUANT_PREFIX}/feature/seed`, {
    method: 'POST',
  });
}

export function refreshFeatureCoverage(): Promise<{
  updated: number;
  kline_start: string | null;
  kline_end: string | null;
  index_start: string | null;
  index_end: string | null;
}> {
  return requestJson(`${QUANT_PREFIX}/feature/refresh-coverage`, {
    method: 'POST',
  });
}

export type FeatureMetaWriteBody = {
  feature_name?: string;
  display_name?: string | null;
  feature_kind?: string;
  source_kind?: string;
  source_path?: string | null;
  source_column?: string | null;
  transform?: string | null;
  frequency?: string;
  domain?: string;
  dtype?: string;
  formula?: string | null;
  enabled?: number;
  sort_order?: number;
  remark?: string | null;
};

export function createFeature(body: FeatureMetaWriteBody): Promise<FeatureMetaItem> {
  return requestJson<FeatureMetaItem>(`${QUANT_PREFIX}/feature`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function updateFeature(
  id: number,
  body: FeatureMetaWriteBody,
): Promise<FeatureMetaItem> {
  return requestJson<FeatureMetaItem>(`${QUANT_PREFIX}/feature/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export function listFactorCombos(): Promise<FactorCombo[]> {
  return requestJson<FactorCombo[]>(`${QUANT_PREFIX}/factor-combo`);
}

export function createFactorCombo(body: {
  name: string;
  items: FactorComboItem[];
  remark?: string | null;
}): Promise<FactorCombo> {
  return requestJson<FactorCombo>(`${QUANT_PREFIX}/factor-combo`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function updateFactorCombo(
  id: number,
  body: {
    name?: string;
    items?: FactorComboItem[];
    remark?: string | null;
  },
): Promise<FactorCombo> {
  return requestJson<FactorCombo>(`${QUANT_PREFIX}/factor-combo/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export function deleteFactorCombo(id: number): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(`${QUANT_PREFIX}/factor-combo/${id}`, {
    method: 'DELETE',
  });
}

export function listBacktestRuns(limit = 50): Promise<BacktestRunItem[]> {
  return requestJson<BacktestRunItem[]>(
    `${QUANT_PREFIX}/backtest/runs?limit=${limit}`,
  );
}

export function getBacktestRun(runId: string): Promise<BacktestRunItem> {
  return requestJson<BacktestRunItem>(
    `${QUANT_PREFIX}/backtest/runs/${encodeURIComponent(runId)}`,
  );
}

export function getBacktestTable(
  runId: string,
  params: {
    name: 'portfolio' | 'trades' | 'returns';
    trade_date?: string;
    group_id?: string;
    ts_code?: string;
    limit?: number;
  },
): Promise<BacktestTableResponse> {
  const query = new URLSearchParams();
  query.set('name', params.name);
  if (params.trade_date) query.set('trade_date', params.trade_date);
  if (params.group_id) query.set('group_id', params.group_id);
  if (params.ts_code) query.set('ts_code', params.ts_code);
  if (params.limit != null) query.set('limit', String(params.limit));
  return requestJson<BacktestTableResponse>(
    `${QUANT_PREFIX}/backtest/runs/${encodeURIComponent(runId)}/tables?${query}`,
  );
}
