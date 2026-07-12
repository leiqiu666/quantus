import type {
  FactorCsResponse,
  QuoteResponse,
  StockKlineResponse,
} from '@/types/quant';
import { requestJson } from '@/utils/request';

const RESEARCH_PREFIX = '/api/admin/research';

export function getFactorCs(params: {
  trade_date: string;
  factor_name?: string;
  combo_id?: number;
}): Promise<FactorCsResponse> {
  const query = new URLSearchParams();
  query.set('trade_date', params.trade_date);
  if (params.factor_name) query.set('factor_name', params.factor_name);
  if (params.combo_id != null) query.set('combo_id', String(params.combo_id));
  return requestJson<FactorCsResponse>(`${RESEARCH_PREFIX}/factor-cs?${query}`);
}

export function getStockKline(params: {
  ts_code: string;
  start: string;
  end: string;
  factor_name?: string;
}): Promise<StockKlineResponse> {
  const query = new URLSearchParams();
  query.set('ts_code', params.ts_code);
  query.set('start', params.start);
  query.set('end', params.end);
  if (params.factor_name) query.set('factor_name', params.factor_name);
  return requestJson<StockKlineResponse>(
    `${RESEARCH_PREFIX}/stock-kline?${query}`,
  );
}

export function getQuote(tsCode: string): Promise<QuoteResponse> {
  const query = new URLSearchParams({ ts_code: tsCode });
  return requestJson<QuoteResponse>(`${RESEARCH_PREFIX}/quote?${query}`);
}
