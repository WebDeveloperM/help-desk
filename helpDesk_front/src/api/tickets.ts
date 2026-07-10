import {
  apiErrorMessage,
  authorizedFetch,
  getApiBase,
  networkErrorMessage,
} from '@/api/client';
import i18n from '@/i18n';
import type {
  Ticket,
  TicketComment,
  TicketCommentListResponse,
  TicketListResponse,
} from '@/types/ticket';

const tErr = (key: string): string => i18n.t(key, { ns: 'errors' });

export type ListTicketsParams = {
  page?: number;
  page_size?: number;
  status?: string;
  priority?: string;
  created_by_id?: string;
  creator_department_id?: string;
  assigned_department_id?: string;
  category_id?: string;
  is_urgent?: boolean;
  created_from?: string;
  created_to?: string;
  search?: string;
};

export type ListTicketsResult =
  | { ok: true; data: TicketListResponse }
  | { ok: false; error: string; status?: number };

export async function listTickets(
  params?: ListTicketsParams
): Promise<ListTicketsResult> {
  const base = getApiBase();
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(params?.page ?? 1));
  searchParams.set('page_size', String(params?.page_size ?? 100));
  if (params?.status) searchParams.set('status', params.status);
  if (params?.priority) searchParams.set('priority', params.priority);
  if (params?.created_by_id) searchParams.set('created_by_id', params.created_by_id);
  if (params?.creator_department_id) searchParams.set('creator_department_id', params.creator_department_id);
  if (params?.assigned_department_id) searchParams.set('assigned_department_id', params.assigned_department_id);
  if (params?.category_id) searchParams.set('category_id', params.category_id);
  if (params?.is_urgent !== undefined) searchParams.set('is_urgent', String(params.is_urgent));
  if (params?.created_from) searchParams.set('created_from', params.created_from);
  if (params?.created_to) searchParams.set('created_to', params.created_to);
  if (params?.search) searchParams.set('search', params.search);

  try {
    const response = await authorizedFetch(`${base}/tickets?${searchParams.toString()}`);

    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('tickets.no_access_all'),
          fallback: tErr('tickets.load'),
        }),
        status: response.status,
      };
    }

    const raw = await response.json();
    const data = normalizeTicketListResponse(raw);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('tickets.load')) };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function normalizeTicket(raw: unknown): Ticket {
  if (!isRecord(raw) || typeof raw.id !== 'string' || typeof raw.status !== 'string') {
    throw new Error(tErr('tickets.malformed_format'));
  }
  const { metadata, ...rest } = raw as Record<string, unknown>;
  return {
    ...rest,
    sla: (raw.sla ?? null) as Ticket['sla'],
    ticket_metadata: (raw.ticket_metadata ?? metadata ?? null) as Ticket['ticket_metadata'],
    progress_percent:
      typeof raw.progress_percent === 'number' ? raw.progress_percent : 0,
  } as Ticket;
}

function normalizeTicketListResponse(raw: unknown): TicketListResponse {
  if (!isRecord(raw)) {
    return { items: [], total: 0, page: 1, page_size: 100, pages: 1 };
  }
  const items = Array.isArray(raw.items) ? raw.items.map(normalizeTicket) : [];
  return {
    items,
    total: typeof raw.total === 'number' ? raw.total : 0,
    page: typeof raw.page === 'number' ? raw.page : 1,
    page_size: typeof raw.page_size === 'number' ? raw.page_size : 100,
    pages: typeof raw.pages === 'number' ? raw.pages : 1,
  };
}

export type TicketCategory = { id: string; name: string; code: string | null };

export type ListTicketCategoriesResult =
  | { ok: true; data: TicketCategory[] }
  | { ok: false; error: string; status?: number };

export async function listTicketCategories(): Promise<ListTicketCategoriesResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/tickets/categories`);
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          fallback: tErr('categories.load'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const list = Array.isArray(raw) ? raw : isRecord(raw) ? (raw.items ?? raw.data ?? []) : [];
    const data: TicketCategory[] = (Array.isArray(list) ? list : [])
      .map((c: unknown) => {
        if (!isRecord(c)) return null;
        const id = typeof c.id === 'string' ? c.id : c.id != null ? String(c.id) : '';
        if (!id) return null;
        return {
          id,
          name: typeof c.name === 'string' ? c.name : String(c.name ?? ''),
          code: c.code != null ? String(c.code) : null,
        };
      })
      .filter((c): c is TicketCategory => c !== null);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('categories.load')) };
  }
}

export type CreateTicketBody = {
  title: string;
  description: string;
  category_id: string;
  creator_department_id: string;
  assigned_department_id?: string | null;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  desired_completion_date?: string | null;
  metadata?: Record<string, unknown> | null;
  executor_user_ids: string[];
};

export type CreateTicketResult =
  | { ok: true; data: Ticket }
  | { ok: false; error: string; status?: number };

export async function createTicket(body: CreateTicketBody): Promise<CreateTicketResult> {
  const base = getApiBase();
  const payload = {
    title: body.title,
    description: body.description,
    category_id: body.category_id,
    creator_department_id: body.creator_department_id,
    assigned_department_id: body.assigned_department_id ?? null,
    priority: body.priority ?? 'normal',
    desired_completion_date: body.desired_completion_date ?? null,
    metadata: body.metadata ?? null,
    executor_user_ids: body.executor_user_ids,
  };
  try {
    const response = await authorizedFetch(`${base}/tickets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('tickets.create_no_access'),
          422: tErr('tickets.create_invalid_data'),
          fallback: tErr('tickets.create'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const data = normalizeTicket(raw);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('tickets.create')) };
  }
}

export type GetTicketByIdResult =
  | { ok: true; data: Ticket }
  | { ok: false; error: string; status?: number };

export async function getTicketById(
  ticketId: string,
  options?: { signal?: AbortSignal }
): Promise<GetTicketByIdResult> {
  const base = getApiBase();

  try {
    const response = await authorizedFetch(`${base}/tickets/${encodeURIComponent(ticketId)}`, {
      signal: options?.signal,
    });

    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('tickets.no_access_one'),
          404: tErr('tickets.not_found'),
          fallback: tErr('tickets.load_one'),
        }),
        status: response.status,
      };
    }

    const raw = await response.json();
    const data = normalizeTicket(raw);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('tickets.load_one')) };
  }
}

export type UpdateTicketBody = {
  title?: string;
  description?: string;
  category_id?: string;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  status?: string;
  assigned_department_id?: string | null;
  desired_completion_date?: string | null;
  metadata?: Record<string, unknown> | null;
  is_urgent?: boolean;
  progress_percent?: number;
};

export type TicketWorkflowResult =
  | { ok: true; data: Ticket }
  | { ok: false; error: string; status?: number };

async function ticketWorkflowRequest(
  ticketId: string,
  method: 'PATCH' | 'POST',
  path: string,
  body?: Record<string, unknown>
): Promise<TicketWorkflowResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/tickets/${encodeURIComponent(ticketId)}${path}`, {
      method,
      headers: {
        ...(body && { 'Content-Type': 'application/json' }),
      },
      ...(body && { body: JSON.stringify(body) }),
    });
    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('no_access'),
          404: tErr('tickets.not_found'),
          422: tErr('invalid_data'),
          fallback: tErr('tickets.operation'),
        }),
        status: response.status,
      };
    }
    const raw = await response.json();
    const data = normalizeTicket(raw);
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('tickets.operation')) };
  }
}

export async function updateTicket(
  ticketId: string,
  body: UpdateTicketBody
): Promise<TicketWorkflowResult> {
  const payload: Record<string, unknown> = {};
  if (body.title !== undefined) payload.title = body.title;
  if (body.description !== undefined) payload.description = body.description;
  if (body.category_id !== undefined) payload.category_id = body.category_id;
  if (body.priority !== undefined) payload.priority = body.priority;
  if (body.status !== undefined) payload.status = body.status;
  if (body.assigned_department_id !== undefined) payload.assigned_department_id = body.assigned_department_id;
  if (body.desired_completion_date !== undefined) payload.desired_completion_date = body.desired_completion_date;
  if (body.is_urgent !== undefined) payload.is_urgent = body.is_urgent;
  if (body.progress_percent !== undefined) payload.progress_percent = body.progress_percent;
  if (body.metadata !== undefined) payload.metadata = body.metadata;
  return ticketWorkflowRequest(ticketId, 'PATCH', '', payload);
}

export async function approveTicket(
  ticketId: string,
  comment?: string | null
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/approve', { comment: comment ?? null });
}

export async function rejectTicket(
  ticketId: string,
  comment: string
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/reject', { comment });
}

export type AssignTicketBody = {
  department_id?: string | null;
  executor_user_ids: string[];
};

export async function assignTicket(
  ticketId: string,
  body: AssignTicketBody
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/assign', {
    department_id: body.department_id ?? null,
    executor_user_ids: body.executor_user_ids,
  });
}

export async function waitingInfoTicket(
  ticketId: string,
  comment?: string | null
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/waiting-info', { comment: comment ?? null });
}

export async function startProgressTicket(
  ticketId: string
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/start-progress');
}

export async function completeTicket(
  ticketId: string,
  comment?: string | null
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/complete', { comment: comment ?? null });
}

export async function closeTicket(
  ticketId: string,
  comment?: string | null
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/close', { comment: comment ?? null });
}

export async function updateTicketProgress(
  ticketId: string,
  progressPercent: number
): Promise<TicketWorkflowResult> {
  return ticketWorkflowRequest(ticketId, 'POST', '/progress', {
    progress_percent: progressPercent,
  });
}

export type GetTicketCommentsResult =
  | { ok: true; data: TicketCommentListResponse }
  | { ok: false; error: string; status?: number };

function normalizeTicketComment(raw: Record<string, unknown>): TicketComment {
  return {
    id: String(raw.id ?? ''),
    ticket_id: String(raw.ticket_id ?? ''),
    author_id: String(raw.author_id ?? ''),
    author_full_name: String(raw.author_full_name ?? ''),
    body: String(raw.body ?? ''),
    created_at: String(raw.created_at ?? ''),
  };
}

export async function getTicketComments(
  token: string,
  ticketId: string,
  page = 1,
  pageSize = 100
): Promise<GetTicketCommentsResult> {
  const base = getApiBase();
  const searchParams = new URLSearchParams();
  searchParams.set('page', String(page));
  searchParams.set('page_size', String(pageSize));
  try {
    const response = await authorizedFetch(
      `${base}/tickets/${encodeURIComponent(ticketId)}/comments?${searchParams.toString()}`,
      { token }
    );
    if (!response.ok) {
      const status = response.status;
      const message =
        status === 401
          ? 'Сессия истекла или нет доступа'
          : status === 403
            ? 'Нет доступа к комментариям этой заявки'
            : 'Ошибка загрузки комментариев';
      return { ok: false, error: message, status };
    }
    const raw = await response.json();
    const items = Array.isArray(raw.items)
      ? (raw.items as Record<string, unknown>[]).map((row) => normalizeTicketComment(row))
      : [];
    const data: TicketCommentListResponse = {
      items,
      total: typeof raw.total === 'number' ? raw.total : 0,
      page: typeof raw.page === 'number' ? raw.page : 1,
      page_size: typeof raw.page_size === 'number' ? raw.page_size : pageSize,
      pages: typeof raw.pages === 'number' ? raw.pages : 0,
    };
    return { ok: true, data };
  } catch {
    return { ok: false, error: 'Ошибка загрузки комментариев' };
  }
}

export type CreateTicketCommentResult =
  | { ok: true; data: TicketComment }
  | { ok: false; error: string; status?: number };

export async function createTicketComment(
  token: string,
  ticketId: string,
  body: string
): Promise<CreateTicketCommentResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(
      `${base}/tickets/${encodeURIComponent(ticketId)}/comments`,
      {
        token,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      }
    );
    if (!response.ok) {
      const status = response.status;
      const text = await response.text();
      let message = 'Не удалось отправить комментарий';
      if (status === 401) message = 'Сессия истекла или нет доступа';
      else if (status === 403) message = 'Нет доступа к этой заявке';
      else if (status === 422) message = 'Проверьте текст комментария';
      else if (text) {
        try {
          const j = JSON.parse(text) as { detail?: unknown };
          const detail = j.detail;
          if (typeof detail === 'string') message = detail;
        } catch {
          /* ignore */
        }
      }
      return { ok: false, error: message, status };
    }
    const raw = (await response.json()) as Record<string, unknown>;
    return { ok: true, data: normalizeTicketComment(raw) };
  } catch (err) {
    const msg = err instanceof Error ? err.message : '';
    return {
      ok: false,
      error: msg.includes('fetch')
        ? 'Не удалось связаться с сервером. Проверьте подключение и URL API.'
        : 'Не удалось отправить комментарий',
    };
  }
}
