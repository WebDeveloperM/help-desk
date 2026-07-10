import { memo, type JSX } from 'react';
import { useTranslation } from 'react-i18next';
import type { Ticket } from '../../types/ticket';
import TicketCard from './TicketCard';
import { cn } from '@/lib/utils';

interface KanbanColumnProps {
  title: string;
  channel?: string;
  active?: boolean;
  tickets: Ticket[];
  onTicketClick?: (ticket: Ticket) => void;
  getCommentsCount?: (ticket: Ticket) => number;
  getTasksCount?: (ticket: Ticket) => number;
}

const KanbanColumn = ({
  title,
  channel,
  active = false,
  tickets,
  onTicketClick,
  getCommentsCount,
  getTasksCount,
}: KanbanColumnProps): JSX.Element => {
  const { t } = useTranslation('dashboard');
  const count = String(tickets.length).padStart(2, '0');

  return (
    <div
      className="flex h-full flex-col"
      role="region"
      aria-label={t('kanban.columnAria', { title, count: tickets.length })}
    >
      <div
        className={cn(
          'mb-3 flex items-baseline justify-between border-t-2 pt-3',
          active ? 'border-accent' : 'border-border',
        )}
      >
        <div className="flex items-baseline gap-2 text-sm font-medium">
          <span className={active ? 'text-accent' : 'text-muted-foreground'}>
            {channel ?? '—'}
          </span>
          <span className="text-foreground">{title}</span>
        </div>
        <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium tabular-nums text-muted-foreground">
          {count}
        </span>
      </div>

      <div className="max-h-[calc(100vh-300px)] flex-1 overflow-y-auto pr-1">
        {tickets.length === 0 ? (
          <div
            className="rounded-2xl border border-dashed border-border px-4 py-10 text-center"
            role="status"
          >
            <p className="text-sm font-medium text-muted-foreground">
              {t('kanban.empty')}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                onClick={() => onTicketClick?.(ticket)}
                commentsCount={getCommentsCount?.(ticket) ?? 0}
                tasksCount={getTasksCount?.(ticket) ?? 0}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(KanbanColumn);
