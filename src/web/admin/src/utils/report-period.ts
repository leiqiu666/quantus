const QUARTER_END_DATES = ['0331', '0630', '0930', '1231'] as const;

/** 与后端 report_period_generate 一致的季度末报告期序列（升序）。 */
export function reportPeriodGenerate(
  startDate: string,
  endDate: string,
): string[] {
  if (!startDate || !endDate || startDate > endDate) {
    return [];
  }

  const startYear = parseInt(startDate.slice(0, 4), 10);
  const endYear = parseInt(endDate.slice(0, 4), 10);
  const periods: string[] = [];

  for (let year = startYear; year <= endYear; year += 1) {
    for (const qend of QUARTER_END_DATES) {
      const period = `${year}${qend}`;
      if (startDate <= period && period <= endDate) {
        periods.push(period);
      }
    }
  }

  return periods;
}

export function formatReportPeriod(period: string): string {
  if (period.length !== 8) {
    return period;
  }
  return `${period.slice(0, 4)}-${period.slice(4, 6)}-${period.slice(6, 8)}`;
}

export function todayYmd(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}
