import i18n from '@/i18n';
import { getStoredAccessToken } from '@/lib/authSession';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
const DEFAULT_TIMEOUT_MS = 30_000;

export function getApiBase(): string {
  if (typeof window !== 'undefined' && !API_BASE_URL.startsWith('http')) {
    return `${window.location.origin}${API_BASE_URL}`;
  }
  return API_BASE_URL;
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<Response> {
  const externalSignal = init.signal;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  if (externalSignal) {
    if (externalSignal.aborted) controller.abort();
    else externalSignal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

export async function getValidAccessToken(
  preferredToken?: string
): Promise<string | undefined> {
  // Single long-lived access token, no refresh: return whatever is stored.
  return getStoredAccessToken() ?? preferredToken;
}

type AuthorizedFetchInit = RequestInit & {
  token?: string;
  timeoutMs?: number;
};

function withAuthorization(
  init: Omit<AuthorizedFetchInit, 'token' | 'timeoutMs'>,
  token: string
): RequestInit {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

export async function authorizedFetch(
  input: RequestInfo | URL,
  init: AuthorizedFetchInit = {}
): Promise<Response> {
  const { token, timeoutMs, ...requestInit } = init;
  const currentToken = await getValidAccessToken(token);
  if (!currentToken) {
    return new Response(null, { status: 401, statusText: 'Unauthorized' });
  }

  return fetchWithTimeout(
    input,
    withAuthorization(requestInit, currentToken),
    timeoutMs
  );
}

export type ApiErrorMap = Record<number, string> & { fallback: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function detailFromBody(body: Record<string, unknown>): string | undefined {
  const detail = body.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (isRecord(d) && typeof d.msg === 'string' ? d.msg : undefined))
      .filter((m): m is string => Boolean(m));
    if (messages.length > 0) return messages.join('; ');
  }
  if (isRecord(detail)) {
    if (typeof detail.message === 'string') return detail.message;
    if (typeof detail.detail === 'string') return detail.detail;
  }
  if (typeof body.message === 'string') return body.message;
  return undefined;
}

/**
 * Translate an API error response.
 *
 * Resolution order:
 *   1. `error_code` from the response body (translated via `errors:codes.<code>`).
 *   2. Status-code mapping from the caller.
 *   3. `detail` field from the body.
 *   4. Caller-provided `fallback`.
 */
export async function apiErrorMessage(
  response: Response,
  map: ApiErrorMap
): Promise<string> {
  let text: string;
  try {
    text = await response.text();
  } catch {
    return map[response.status] ?? map.fallback;
  }
  if (!text) {
    return map[response.status] ?? map.fallback;
  }

  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    const direct = map[response.status];
    if (direct) return direct;
    return text.length < 300 ? text : map.fallback;
  }

  if (isRecord(body)) {
    const code = body.error_code;
    if (typeof code === 'string' && code) {
      const params = isRecord(body.error_params)
        ? (body.error_params as Record<string, unknown>)
        : undefined;
      const translated = i18n.t(`codes.${code}`, {
        ns: 'errors',
        defaultValue: '',
        ...params,
      });
      if (translated) return translated;
    }
    const direct = map[response.status];
    if (direct) return direct;
    const fromBody = detailFromBody(body);
    if (fromBody) return fromBody;
  } else {
    const direct = map[response.status];
    if (direct) return direct;
  }

  return map.fallback;
}

export function networkErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return i18n.t('network_aborted', { ns: 'errors' });
  }
  if (err instanceof TypeError) {
    return i18n.t('network_unreachable', { ns: 'errors' });
  }
  return fallback;
}
