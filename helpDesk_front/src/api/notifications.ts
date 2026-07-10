import {
  apiErrorMessage,
  authorizedFetch,
  getApiBase,
  networkErrorMessage,
} from '@/api/client';
import i18n from '@/i18n';

const loadError = (): string =>
  i18n.t('notifications.loadError', {
    ns: 'common',
    defaultValue: 'Не удалось загрузить уведомления',
  });

export type NotificationItem = {
  id: string;
  ticket_id: string | null;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type ListNotificationsParams = {
  page?: number;
  page_size?: number;
  is_read?: boolean;
};

export type ListNotificationsResult =
  | { ok: true; data: NotificationListResponse }
  | { ok: false; error: string; status?: number };

export type UnreadCountResult =
  | { ok: true; data: number }
  | { ok: false; error: string; status?: number };

export type MarkAllReadResult =
  | { ok: true; data: { marked_count: number } }
  | { ok: false; error: string; status?: number };

export type MarkReadResult =
  | { ok: true; data: NotificationItem }
  | { ok: false; error: string; status?: number };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function normalizeNotification(raw: unknown): NotificationItem {
  const r = isRecord(raw) ? raw : {};
  return {
    id: String(r.id ?? ''),
    ticket_id:
      typeof r.ticket_id === 'string' && r.ticket_id ? r.ticket_id : null,
    notification_type:
      typeof r.notification_type === 'string' ? r.notification_type : '',
    title: typeof r.title === 'string' ? r.title : '',
    message: typeof r.message === 'string' ? r.message : '',
    is_read: r.is_read === true,
    created_at: typeof r.created_at === 'string' ? r.created_at : '',
  };
}

function normalizeListResponse(
  raw: unknown,
  fallbackPageSize: number
): NotificationListResponse {
  if (!isRecord(raw)) {
    return { items: [], total: 0, page: 1, page_size: fallbackPageSize, pages: 1 };
  }
  const items = Array.isArray(raw.items)
    ? raw.items.map(normalizeNotification).filter((n) => n.id)
    : [];
  return {
    items,
    total: typeof raw.total === 'number' ? raw.total : items.length,
    page: typeof raw.page === 'number' ? raw.page : 1,
    page_size:
      typeof raw.page_size === 'number' ? raw.page_size : fallbackPageSize,
    pages: typeof raw.pages === 'number' ? raw.pages : 1,
  };
}

export async function listNotifications(
  params?: ListNotificationsParams
): Promise<ListNotificationsResult> {
  const base = getApiBase();
  const pageSize = params?.page_size ?? 15;
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(params?.page ?? 1));
  searchParams.set('page_size', String(pageSize));
  if (params?.is_read !== undefined) {
    searchParams.set('is_read', String(params.is_read));
  }

  try {
    const response = await authorizedFetch(
      `${base}/notifications?${searchParams.toString()}`
    );
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, { fallback: loadError() }),
        status: response.status,
      };
    }
    const raw = await response.json();
    return { ok: true, data: normalizeListResponse(raw, pageSize) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, loadError()) };
  }
}

export async function getUnreadCount(): Promise<UnreadCountResult> {
  const result = await listNotifications({ page: 1, page_size: 1, is_read: false });
  if (!result.ok) {
    return { ok: false, error: result.error, status: result.status };
  }
  return { ok: true, data: result.data.total };
}

export async function markAllRead(): Promise<MarkAllReadResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/notifications/read-all`, {
      method: 'POST',
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, { fallback: loadError() }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const marked =
      isRecord(raw) && typeof raw.marked_count === 'number'
        ? raw.marked_count
        : 0;
    return { ok: true, data: { marked_count: marked } };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, loadError()) };
  }
}

export async function markRead(id: string): Promise<MarkReadResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(
      `${base}/notifications/${encodeURIComponent(id)}/read`,
      { method: 'POST' }
    );
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, { fallback: loadError() }),
        status: response.status,
      };
    }
    const raw = await response.json();
    return { ok: true, data: normalizeNotification(raw) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, loadError()) };
  }
}
