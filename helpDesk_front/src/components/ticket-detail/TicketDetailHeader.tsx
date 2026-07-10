import { useTranslation } from 'react-i18next';
import type { Ticket } from '@/types/ticket';
import { CircularProgress } from '@/components/ui/circular-progress';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  AlertTriangle,
  Laptop,
  Wrench,
  Cog,
} from 'lucide-react';
import {
  getStatusColor,
  getStatusLabel,
  getPriorityColor,
  getPriorityLabel,
  getAssetType,
  getAssetTypeLabel,
  getSlaBadge,
} from '@/lib/ticketFormatters';

interface TicketDetailHeaderProps {
  ticket: Ticket;
  onBack: () => void;
}

const TicketDetailHeader = ({ ticket, onBack }: TicketDetailHeaderProps) => {
  const { t } = useTranslation('tickets');
  const assetType = getAssetType(ticket.id);
  const AssetIcon = assetType === 'laptop' ? Laptop : assetType === 'equipment' ? Wrench : Cog;
  const slaBadge = getSlaBadge(ticket.sla?.status);

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-2 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground transition-colors mb-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={t('detail.back')}
      >
        <ArrowLeft className="w-4 h-4" aria-hidden />
        <span>{t('detail.back')}</span>
      </button>

      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <div
              className={cn(
                'p-3 rounded-2xl',
                assetType === 'laptop' && 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
                assetType === 'equipment' && 'bg-accent/12 text-accent',
                assetType === 'component' && 'bg-purple-500/10 text-purple-600 dark:text-purple-400'
              )}
              aria-hidden
            >
              <AssetIcon className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-display text-2xl md:text-3xl font-bold text-foreground mb-2">
                {ticket.title}
              </h1>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-muted-foreground">
                  #{ticket.ticket_number}
                </span>
                <span className="text-muted-foreground" aria-hidden>•</span>
                <span className="text-sm text-muted-foreground capitalize">
                  {getAssetTypeLabel(assetType)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-medium border',
                getStatusColor(ticket.status)
              )}
            >
              {getStatusLabel(ticket.status)}
            </span>
            <span
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-medium border',
                getPriorityColor(ticket.priority)
              )}
            >
              {getPriorityLabel(ticket.priority)}
            </span>
            {ticket.is_urgent && (
              <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium bg-destructive/12 text-destructive border border-destructive/30">
                <AlertTriangle className="w-4 h-4" aria-hidden />
                {t('detail.urgent')}
              </span>
            )}
            {slaBadge && (
              <span
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium border',
                  slaBadge.className
                )}
              >
                {slaBadge.label}
              </span>
            )}
          </div>
          <div className="mt-4 flex items-center gap-3">
            <CircularProgress value={ticket.progress_percent} size={72} strokeWidth={7} aria-label={t('detail.progressAria', { value: ticket.progress_percent })} />
            <div className="text-xs font-medium text-muted-foreground">
              {t('detail.implementation')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TicketDetailHeader;
