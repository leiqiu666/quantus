/** Admin SSE 补位/入库任务并发上限（根目录 .env：`VITE_ETL_SSE_MAX_CONCURRENT`） */
const raw = import.meta.env.VITE_ETL_SSE_MAX_CONCURRENT;
const parsed = raw !== undefined && raw !== '' ? Number.parseInt(String(raw), 10) : 5;

export const ETL_SSE_MAX_CONCURRENT = Number.isFinite(parsed) && parsed >= 1
  ? parsed
  : 5;
