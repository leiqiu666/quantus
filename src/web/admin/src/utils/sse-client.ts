import { requestFetch } from '@/utils/request';

export type SseEventPayload = Record<string, unknown>;

export async function consumeSsePost(
  url: string,
  body: unknown,
  onEvent: (event: SseEventPayload) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await requestFetch(url, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const errBody = await response.json();
      if (typeof errBody === 'object' && errBody && 'detail' in errBody) {
        detail = String((errBody as { detail: unknown }).detail);
      }
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('响应体不可读');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      const line = part
        .split('\n')
        .find((l) => l.startsWith('data:'));
      if (!line) {
        continue;
      }
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) {
        continue;
      }
      try {
        onEvent(JSON.parse(jsonStr) as SseEventPayload);
      } catch {
        // skip malformed frame
      }
    }
  }

  if (buffer.trim()) {
    const line = buffer
      .split('\n')
      .find((l) => l.startsWith('data:'));
    if (line) {
      const jsonStr = line.slice(5).trim();
      if (jsonStr) {
        try {
          onEvent(JSON.parse(jsonStr) as SseEventPayload);
        } catch {
          // skip
        }
      }
    }
  }
}
