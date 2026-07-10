import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import i18n, { LANGUAGE_HTML_LANG, isSupportedLanguage } from '@/i18n';
import { TicketSlaStatus, type Ticket } from '../../types/ticket';
import { cn } from '@/lib/utils';
import {
  AlertTriangle,
  ArrowUpRight,
  CheckSquare,
  Clock,
  MessageSquare,
  User,
} from 'lucide-react';

interface TicketCardProps {
  ticket: Ticket;
  onClick?: () => void;
  commentsCount?: number;
  tasksCount?: number;
}

const slaToneFor = (status: TicketSlaStatus | undefined): string | null => {
  switch (status) {
    case TicketSlaStatus.ON_TRACK:
    case TicketSlaStatus.COMPLETED_ON_TIME:
      return 'text-success';
    case TicketSlaStatus.AT_RISK:
      return 'text-warning';
    case TicketSlaStatus.OVERDUE:
    case TicketSlaStatus.COMPLETED_LATE:
      return 'text-destructive';
    default:
      return null;
  }
};

const slaShortKey: Partial<Record<TicketSlaStatus, string>> = {
  [TicketSlaStatus.ON_TRACK]: 'sla.short.onTrack',
  [TicketSlaStatus.AT_RISK]: 'sla.short.atRisk',
  [TicketSlaStatus.OVERDUE]: 'sla.short.overdue',
  [TicketSlaStatus.COMPLETED_ON_TIME]: 'sla.short.completedOnTime',
  [TicketSlaStatus.COMPLETED_LATE]: 'sla.short.completedLate',
};

const formatDate = (iso: string | null): string => {
  if (!iso) return '—';
  const lng = i18n.resolvedLanguage ?? i18n.language ?? 'ru';
  const base = lng.split('-')[0];
  const locale = isSupportedLanguage(base) ? LANGUAGE_HTML_LANG[base] : 'ru';
  return new Date(iso).toLocaleDateString(locale, {
    day: '2-digit',
    month: 'short',
  });
};

const TicketCard = ({
  ticket,
  onClick,
  commentsCount = 0,
  tasksCount = 0,
}: TicketCardProps): ReactNode => {
  const { t } = useTranslation('tickets');
  const slaTone = slaToneFor(ticket.sla?.status);
  const slaKey = ticket.sla?.status ? slaShortKey[ticket.sla.status] : undefined;
  const slaLabel = slaKey ? t(slaKey) : null;
  const isPastSla =
    ticket.sla?.status === TicketSlaStatus.OVERDUE ||
    ticket.sla?.status === TicketSlaStatus.COMPLETED_LATE;
  const isUrgent = ticket.is_urgent || ticket.priority === 'urgent';
  const dueDate =
    ticket.sla?.planned_completion_date ??
    ticket.planned_completion_date ??
    ticket.desired_completion_date;
  const progress = Math.max(0, Math.min(100, ticket.progress_percent ?? 0));

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <article
      tabIndex={0}
      role="button"
      onClick={onClick}
      onKeyDown={handleKeyDown}
      aria-label={t('card.aria', { number: ticket.ticket_number, title: ticket.title })}
      className={cn(
        'group relative cursor-pointer rounded-2xl border bg-card p-5 shadow-sm transition-colors',
        'hover:border-accent/40 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
        isPastSla && 'border-destructive/40',
        isUrgent && !isPastSla && 'border-accent/60',
        !isPastSla && !isUrgent && 'border-border',
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium tabular-nums text-muted-foreground">
          #{ticket.ticket_number}
        </span>
        <div className="flex items-center gap-2">
          {isUrgent && (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/12 px-2.5 py-1 text-xs font-medium text-accent">
              <AlertTriangle className="h-3 w-3" aria-hidden />
              {t('card.urgentBadge')}
            </span>
          )}
          <ArrowUpRight
            className="h-3.5 w-3.5 text-muted-foreground opacity-40 transition-transform duration-150 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:opacity-90"
            aria-hidden
          />
        </div>
      </div>

      <h4 className="font-display mb-2 text-[17px] leading-snug tracking-[-0.01em] text-foreground line-clamp-2">
        {ticket.title}
      </h4>

      {(ticket.created_by?.full_name || ticket.creator_department?.name) && (
        <div className="mb-3 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
          <User className="h-3.5 w-3.5 flex-none" aria-hidden />
          <span className="truncate">
            {ticket.created_by?.full_name ?? '—'}
            {ticket.creator_department?.name ? ` · ${ticket.creator_department.name}` : ''}
          </span>
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-medium">
        <span className="rounded-full bg-muted px-2.5 py-1 text-muted-foreground">
          {t(`shortStatus.${ticket.status}`, { defaultValue: ticket.status.toUpperCase() })}
        </span>
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1',
            ticket.priority === 'urgent' && 'bg-destructive/12 text-destructive',
            ticket.priority === 'high' && 'bg-accent/12 text-accent',
            (ticket.priority === 'low' || ticket.priority === 'normal') &&
              'bg-muted text-muted-foreground',
          )}
        >
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              ticket.priority === 'urgent' && 'bg-destructive',
              ticket.priority === 'high' && 'bg-accent',
              (ticket.priority === 'low' || ticket.priority === 'normal') &&
                'bg-muted-foreground',
            )}
            aria-hidden
          />
          {t(`shortPriority.${ticket.priority}`, { defaultValue: ticket.priority.toUpperCase() })}
        </span>
        {slaLabel && slaTone && (
          <span className={cn('rounded-full bg-muted px-2.5 py-1', slaTone)}>{slaLabel}</span>
        )}
      </div>

      <div className="mb-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-accent transition-all duration-300"
            style={{ width: `${progress}%` }}
            aria-hidden
          />
        </div>
        <div className="mt-2 flex items-center justify-between text-xs tabular-nums text-muted-foreground">
          <span>{progress.toFixed(0)}%</span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" aria-hidden />
            {formatDate(dueDate)}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 text-xs tabular-nums text-muted-foreground">
        <span className="flex items-center gap-1">
          <MessageSquare className="h-3 w-3" aria-hidden />
          {commentsCount}
        </span>
        <span className="flex items-center gap-1">
          <CheckSquare className="h-3 w-3" aria-hidden />
          {tasksCount}
        </span>
      </div>
    </article>
  );
};

export default TicketCard;
