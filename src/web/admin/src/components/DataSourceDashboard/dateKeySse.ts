export function dateKeyToSseRange(
  dateKey: string,
  dateKeyType: string,
): { startDate: string; endDate: string } {
  if (dateKeyType === 'month' && dateKey.length === 6) {
    const y = Number(dateKey.slice(0, 4));
    const m = Number(dateKey.slice(4, 6));
    const lastDay = new Date(y, m, 0).getDate();
    return {
      startDate: `${dateKey}01`,
      endDate: `${dateKey}${String(lastDay).padStart(2, '0')}`,
    };
  }
  return { startDate: dateKey, endDate: dateKey };
}

export function searchRangeToSseRange(
  start: string,
  end: string,
  dateKeyType?: string,
): { startDate: string; endDate: string } {
  if (dateKeyType === 'month' && start.length === 6) {
    const sy = start.slice(0, 4);
    const sm = start.slice(4, 6);
    const ey = end.slice(0, 4);
    const em = end.slice(4, 6);
    const lastDay = new Date(Number(ey), Number(em), 0).getDate();
    return {
      startDate: `${sy}${sm}01`,
      endDate: `${ey}${em}${String(lastDay).padStart(2, '0')}`,
    };
  }
  return { startDate: start, endDate: end };
}
