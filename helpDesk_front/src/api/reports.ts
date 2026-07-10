import {
  apiErrorMessage,
  authorizedFetch,
  getApiBase,
  networkErrorMessage,
} from '@/api/client';
import i18n from '@/i18n';

const tErr = (key: string): string => i18n.t(key, { ns: 'errors' });

export type StatusCount = { status: string; count: number };
export type PriorityCount = { priority: string; count: number };
export type CategoryCount = { category_id: string; name: string; count: number };
export type ThroughputPoint = { date: string; created: number; completed: number };

export type TicketStats = {
  total: number;
  open: number;
  in_progress: number;
  completed: number;
  closed: number;
  overdue: number;
  urgent_open: number;
  created_last_7d: number;
  completed_last_7d: number;
  avg_resolution_hours: number | null;
  sla_compliance_pct: number | null;
  by_status: StatusCount[];
  by_priority: PriorityCount[];
  by_category: CategoryCount[];
  throughput: ThroughputPoint[];
};

export type GetTicketStatsResult =
  | { ok: true; data: TicketStats }
  | { ok: false; error: string; status?: number };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

const toNumber = (value: unknown, fallback = 0): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

const toNullableNumber = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const toStatusCounts = (value: unknown): StatusCount[] =>
  Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((row) => ({
          status: String(row.status ?? ''),
          count: toNumber(row.count),
        }))
    : [];

const toPriorityCounts = (value: unknown): PriorityCount[] =>
  Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((row) => ({
          priority: String(row.priority ?? ''),
          count: toNumber(row.count),
        }))
    : [];

const toCategoryCounts = (value: unknown): CategoryCount[] =>
  Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((row) => ({
          category_id: String(row.category_id ?? ''),
          name: String(row.name ?? ''),
          count: toNumber(row.count),
        }))
    : [];

const toThroughput = (value: unknown): ThroughputPoint[] =>
  Array.isArray(value)
    ? value
        .filter(isRecord)
        .map((row) => ({
          date: String(row.date ?? ''),
          created: toNumber(row.created),
          completed: toNumber(row.completed),
        }))
    : [];

function normalizeStats(raw: unknown): TicketStats {
  if (!isRecord(raw)) {
    return {
      total: 0,
      open: 0,
      in_progress: 0,
      completed: 0,
      closed: 0,
      overdue: 0,
      urgent_open: 0,
      created_last_7d: 0,
      completed_last_7d: 0,
      avg_resolution_hours: null,
      sla_compliance_pct: null,
      by_status: [],
      by_priority: [],
      by_category: [],
      throughput: [],
    };
  }
  return {
    total: toNumber(raw.total),
    open: toNumber(raw.open),
    in_progress: toNumber(raw.in_progress),
    completed: toNumber(raw.completed),
    closed: toNumber(raw.closed),
    overdue: toNumber(raw.overdue),
    urgent_open: toNumber(raw.urgent_open),
    created_last_7d: toNumber(raw.created_last_7d),
    completed_last_7d: toNumber(raw.completed_last_7d),
    avg_resolution_hours: toNullableNumber(raw.avg_resolution_hours),
    sla_compliance_pct: toNullableNumber(raw.sla_compliance_pct),
    by_status: toStatusCounts(raw.by_status),
    by_priority: toPriorityCounts(raw.by_priority),
    by_category: toCategoryCounts(raw.by_category),
    throughput: toThroughput(raw.throughput),
  };
}

export async function getTicketStats(options?: {
  signal?: AbortSignal;
}): Promise<GetTicketStatsResult> {
  const base = getApiBase();
  try {
    const response = await authorizedFetch(`${base}/tickets/stats`, {
      signal: options?.signal,
    });

    if (!response.ok) {
      return {
        ok: false,
        error: await apiErrorMessage(response, {
          401: tErr('session_expired'),
          403: tErr('no_access'),
          fallback: tErr('tickets.load'),
        }),
        status: response.status,
      };
    }

    const raw = await response.json();
    return { ok: true, data: normalizeStats(raw) };
  } catch (err) {
    return { ok: false, error: networkErrorMessage(err, tErr('tickets.load')) };
  }
}
