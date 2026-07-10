import { useTranslation } from 'react-i18next';
import type { Ticket } from '@/types/ticket';
import { TicketStatus } from '@/types/ticket';
import {
  Check,
  X,
  UserPlus,
  Play,
  CheckCircle,
  Archive,
  PauseCircle,
  Loader2,
} from 'lucide-react';

interface TicketDetailActionsProps {
  ticket: Ticket;
  workflowLoading: boolean;
  onOpenModal: (modal: 'approve' | 'reject' | 'assign' | 'complete' | 'close') => void;
  onStartProgress: () => void;
  onWaitingInfo: () => void;
}

const TicketDetailActions = ({
  ticket,
  workflowLoading,
  onOpenModal,
  onStartProgress,
  onWaitingInfo,
}: TicketDetailActionsProps) => {
  const { t } = useTranslation('tickets');
  const startWorkLabel =
    ticket.status === TicketStatus.WAITING_INFO
      ? t('actions.resumeWork')
      : t('actions.startWork');

  return (
    <div className="flex items-center gap-2 flex-wrap" role="group" aria-label={t('detail.actionsAria')}>
      {ticket.status === TicketStatus.PENDING_APPROVAL && (
        <>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            onClick={() => onOpenModal('approve')}
            aria-label={t('actions.approveAria')}
          >
            <Check className="w-4 h-4" aria-hidden />
            {t('actions.approve')}
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/15 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
            onClick={() => onOpenModal('reject')}
            aria-label={t('actions.rejectAria')}
          >
            <X className="w-4 h-4" aria-hidden />
            {t('actions.reject')}
          </button>
        </>
      )}
      {ticket.status === TicketStatus.APPROVED && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          onClick={() => onOpenModal('assign')}
          aria-label={t('actions.assignAria')}
        >
          <UserPlus className="w-4 h-4" aria-hidden />
          {t('actions.assign')}
        </button>
      )}
      {(ticket.status === TicketStatus.ASSIGNED || ticket.status === TicketStatus.WAITING_INFO) && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:opacity-50"
          onClick={() => void onStartProgress()}
          disabled={workflowLoading}
          aria-label={startWorkLabel}
        >
          {workflowLoading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <Play className="w-4 h-4" aria-hidden />}
          {startWorkLabel}
        </button>
      )}
      {ticket.status === TicketStatus.IN_PROGRESS && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold border border-border bg-card text-foreground hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:opacity-50"
          onClick={() => void onWaitingInfo()}
          disabled={workflowLoading}
          aria-label={t('actions.waitingInfo')}
        >
          {workflowLoading ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : <PauseCircle className="w-4 h-4" aria-hidden />}
          {t('actions.waitingInfo')}
        </button>
      )}
      {(ticket.status === TicketStatus.IN_PROGRESS || ticket.status === TicketStatus.WAITING_INFO) && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold bg-accent text-accent-foreground hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          onClick={() => onOpenModal('complete')}
          aria-label={t('actions.completeAria')}
        >
          <CheckCircle className="w-4 h-4" aria-hidden />
          {t('actions.complete')}
        </button>
      )}
      {ticket.status === TicketStatus.COMPLETED && (
        <button
          type="button"
          className="inline-flex items-center justify-center gap-2 px-4 h-10 rounded-xl text-sm font-semibold border border-border bg-card text-foreground hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          onClick={() => onOpenModal('close')}
          aria-label={t('actions.closeAria')}
        >
          <Archive className="w-4 h-4" aria-hidden />
          {t('actions.close')}
        </button>
      )}
    </div>
  );
};

export default TicketDetailActions;
