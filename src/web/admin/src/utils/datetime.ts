import dayjs from 'dayjs';

/** ISO / datetime 字符串 → `YYYY-MM-DD HH:mm:ss` */
export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—';
  }
  if (/^\d{8}T\d{6}$/.test(value)) {
    const parsed = dayjs(value, 'YYYYMMDDTHHmmss');
    return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
  }
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : value;
}
