import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string;
  channel?: string;
  hint?: string;
  active?: boolean;
  icon?: LucideIcon;
  className?: string;
  children?: ReactNode;
}

const StatCard = ({
  title,
  value,
  channel,
  hint,
  active = false,
  icon: Icon,
  className,
  children,
}: StatCardProps): ReactNode => (
  <article
    aria-label={`${title}: ${value}${hint ? ` (${hint})` : ''}`}
    className={cn(
      'group relative rounded-2xl bg-card border border-border p-5 shadow-sm transition-colors md:p-6',
      'hover:border-accent/40',
      className,
    )}
  >
    <div className="mb-5 flex items-center justify-between text-xs font-medium text-muted-foreground">
      <span className="flex items-center gap-2">
        {active && (
          <span className="relative inline-flex h-1.5 w-1.5 items-center justify-center">
            <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-50" aria-hidden />
            <span className="relative h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
          </span>
        )}
        <span className="tabular-nums">{channel ?? '—'}</span>
        <span className="text-border">/</span>
        <span>{title}</span>
      </span>
      {Icon && <Icon className="h-4 w-4 text-muted-foreground/70" aria-hidden />}
    </div>

    <div className="flex items-baseline gap-3">
      <div className="font-display text-[44px] font-light leading-none tracking-[-0.03em] tabular-nums text-foreground">
        {value}
      </div>
      {hint && (
        <div className="pb-1 text-xs font-medium text-muted-foreground">
          {hint}
        </div>
      )}
    </div>

    {children}
  </article>
);

export default StatCard;
