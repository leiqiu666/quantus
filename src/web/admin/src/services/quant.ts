import type {
  BacktestRunItem,
  BacktestTableResponse,
  FactorCombo,
  FactorComboItem,
  FactorMetaItem,
} from '@/types/quant';
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
