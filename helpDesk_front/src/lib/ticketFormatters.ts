import i18n, { LANGUAGE_HTML_LANG, isSupportedLanguage, type SupportedLanguage } from '@/i18n';
import { TicketSlaStatus } from '@/types/ticket';

export function hashStringToIndex(str: string, max: number): number {
  return [...str].reduce((acc, c) => acc + c.charCodeAt(0), 0) % max;
}

const resolveLanguage = (): SupportedLanguage => {
  const lng = i18n.resolvedLanguage ?? i18n.language ?? 'ru';
  const base = lng.split('-')[0];
  return isSupportedLanguage(base) ? base : 'ru';
};

const resolveLocale = (): string => LANGUAGE_HTML_LANG[resolveLanguage()];

const notSpecified = (): string => i18n.t('formatters.notSpecified', { ns: 'common' });

export function formatDate(dateString: string | null): string {
  if (!dateString) return notSpecified();
  const date = new Date(dateString);
  return date.toLocaleDateString(resolveLocale(), {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDateShort(dateString: string | null): string {
  if (!dateString) return notSpecified();
  const date = new Date(dateString);
  return date.toLocaleDateString(resolveLocale(), { day: 'numeric', month: 'short' });
}

export function getStatusColor(status: string): string {
  const statusColors: Record<string, string> = {
    draft: 'bg-navy-100 dark:bg-navy-800 text-navy-700 dark:text-navy-300',
    pending_approval: 'bg-safety-amber/20 text-safety-amber border border-safety-amber/30',
    approved: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
    assigned: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20',
    in_progress: 'bg-safety-orange/20 text-safety-orange border border-safety-orange/30',
    waiting_info: 'bg-safety-amber/20 text-safety-amber border border-safety-amber/30',
    completed: 'bg-success/20 text-success border border-success/30',
    closed: 'bg-muted text-muted-foreground border border-border',
    rejected: 'bg-destructive/20 text-destructive border border-destructive/30',
  };
  return statusColors[status] || 'bg-muted text-muted-foreground';
}

export function getPriorityColor(priority: string): string {
  const priorityColors: Record<string, string> = {
    low: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
    normal: 'bg-muted text-muted-foreground border-border',
    high: 'bg-safety-orange/20 text-safety-orange border-safety-orange/30',
    urgent: 'bg-destructive/20 text-destructive border-destructive/30',
  };
  return priorityColors[priority] || 'bg-muted text-muted-foreground border-border';
}

const STATUS_KEYS: ReadonlySet<string> = new Set([
  'draft',
  'pending_approval',
  'approved',
  'assigned',
  'in_progress',
  'waiting_info',
  'completed',
  'closed',
  'rejected',
]);

const PRIORITY_KEYS: ReadonlySet<string> = new Set(['low', 'normal', 'high', 'urgent']);

export function getStatusLabel(status: string): string {
  if (!STATUS_KEYS.has(status)) return status;
  return i18n.t(`status.${status}`, { ns: 'tickets' });
}

export function getPriorityLabel(priority: string): string {
  if (!PRIORITY_KEYS.has(priority)) return priority;
  return i18n.t(`priority.${priority}`, { ns: 'tickets' });
}

export function getAssetType(ticketId: string): 'laptop' | 'equipment' | 'component' {
  const assetTypes: ('laptop' | 'equipment' | 'component')[] = ['laptop', 'equipment', 'component'];
  return assetTypes[hashStringToIndex(ticketId, 3)] || 'laptop';
}

export function getAssetTypeLabel(assetType: 'laptop' | 'equipment' | 'component'): string {
  return i18n.t(`asset.${assetType}`, { ns: 'tickets' });
}

export function getSlaBadge(slaStatus: string | undefined): { label: string; className: string } | null {
  switch (slaStatus) {
    case TicketSlaStatus.ON_TRACK:
      return {
        label: i18n.t('sla.onTrack', { ns: 'tickets' }),
        className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
      };
    case TicketSlaStatus.AT_RISK:
      return {
        label: i18n.t('sla.atRisk', { ns: 'tickets' }),
        className: 'bg-safety-amber/20 text-safety-amber border border-safety-amber/30',
      };
    case TicketSlaStatus.OVERDUE:
      return {
        label: i18n.t('sla.overdue', { ns: 'tickets' }),
        className: 'bg-destructive/20 text-destructive border border-destructive/30',
      };
    case TicketSlaStatus.COMPLETED_ON_TIME:
      return {
        label: i18n.t('sla.completedOnTime', { ns: 'tickets' }),
        className: 'bg-success/20 text-success border border-success/30',
      };
    case TicketSlaStatus.COMPLETED_LATE:
      return {
        label: i18n.t('sla.completedLate', { ns: 'tickets' }),
        className: 'bg-destructive/20 text-destructive border border-destructive/30',
      };
    default:
      return null;
  }
}
