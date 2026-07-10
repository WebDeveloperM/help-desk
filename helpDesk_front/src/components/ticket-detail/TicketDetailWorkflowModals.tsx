import { useTranslation } from 'react-i18next';
import type { Ticket } from '@/types/ticket';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { AlertCircle, Loader2 } from 'lucide-react';

export type WorkflowModalType = 'approve' | 'reject' | 'assign' | 'complete' | 'close' | null;

interface TicketDetailWorkflowModalsProps {
  workflowModal: WorkflowModalType;
  onClose: () => void;
  workflowComment: string;
  onCommentChange: (value: string) => void;
  workflowError: string | null;
  workflowLoading: boolean;
  assignExecutorIds: string[];
  assignUsers: { id: string; full_name: string; email: string }[];
  onExecutorToggle: (userId: string) => void;
  ticket: Ticket | null;
  onApprove: () => void;
  onReject: () => void;
  onAssign: () => void;
  onComplete: () => void;
  onCloseTicket: () => void;
}

const TicketDetailWorkflowModals = ({
  workflowModal,
  onClose,
  workflowComment,
  onCommentChange,
  workflowError,
  workflowLoading,
  assignExecutorIds,
  assignUsers,
  onExecutorToggle,
  ticket,
  onApprove,
  onReject,
  onAssign,
  onComplete,
  onCloseTicket,
}: TicketDetailWorkflowModalsProps) => {
  const { t } = useTranslation('tickets');
  const { t: tCommon } = useTranslation('common');
  const errorBlock = workflowError ? (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-xl border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
      <span>{workflowError}</span>
    </div>
  ) : null;

  return (
    <>
      <Dialog open={workflowModal === 'approve'} onOpenChange={(open) => !open && onClose()}>
        <DialogContent aria-describedby="approve-description">
          <DialogHeader>
            <DialogTitle>{t('workflow.modals.approveTitle')}</DialogTitle>
            <DialogDescription id="approve-description">{t('workflow.modals.approveDesc')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {errorBlock}
            <div className="space-y-2">
              <label htmlFor="approve-comment" className="text-sm font-medium">
                {t('workflow.modals.commentLabel')}
              </label>
              <textarea
                id="approve-comment"
                value={workflowComment}
                onChange={(e) => onCommentChange(e.target.value)}
                rows={3}
                className="flex w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
                placeholder={t('workflow.modals.commentOptionalPlaceholder')}
                aria-describedby="approve-description"
              />
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center px-4 h-10 text-sm font-semibold border border-border bg-card text-foreground rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="button"
              onClick={onApprove}
              disabled={workflowLoading}
              className="inline-flex items-center justify-center gap-2 px-4 h-10 text-sm font-semibold bg-accent text-accent-foreground rounded-xl hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {workflowLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
              {t('actions.approve')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={workflowModal === 'reject'} onOpenChange={(open) => !open && onClose()}>
        <DialogContent aria-describedby="reject-description">
          <DialogHeader>
            <DialogTitle>{t('workflow.modals.rejectTitle')}</DialogTitle>
            <DialogDescription id="reject-description">{t('workflow.modals.rejectDesc')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {errorBlock}
            <div className="space-y-2">
              <label htmlFor="reject-comment" className="text-sm font-medium">
                {t('workflow.modals.rejectReasonLabel')} <span className="text-destructive">*</span>
              </label>
              <textarea
                id="reject-comment"
                value={workflowComment}
                onChange={(e) => onCommentChange(e.target.value)}
                rows={4}
                className="flex w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
                placeholder={t('workflow.modals.rejectReasonPlaceholder')}
                aria-required
                aria-describedby="reject-description"
              />
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center px-4 h-10 text-sm font-semibold border border-border bg-card text-foreground rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="button"
              onClick={onReject}
              disabled={workflowLoading || !workflowComment.trim()}
              className="inline-flex items-center justify-center gap-2 px-4 h-10 text-sm font-semibold bg-destructive text-destructive-foreground rounded-xl hover:bg-destructive/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
            >
              {workflowLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
              {t('actions.reject')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={workflowModal === 'assign'} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-md" aria-describedby="assign-description">
          <DialogHeader>
            <DialogTitle>{t('workflow.modals.assignTitle')}</DialogTitle>
            <DialogDescription id="assign-description">{t('workflow.modals.assignDesc')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {errorBlock}
            <div className="space-y-2">
              <span className="text-sm font-medium">{t('workflow.modals.assignDepartmentLabel')}</span>
              <div className="rounded-xl border border-border bg-muted px-3.5 py-2.5 text-[15px] text-foreground">
                {ticket?.assigned_department?.name ||
                  ticket?.creator_department?.name ||
                  t('workflow.modals.creatorDeptFallback')}
              </div>
            </div>
            {assignUsers.length > 0 && (
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t('workflow.modals.assignExecutorsLabel')} <span className="text-destructive">*</span>
                </label>
                <div className="rounded-xl border border-border bg-background p-3 max-h-32 overflow-y-auto space-y-2">
                  {assignUsers.map((u) => (
                    <label
                      key={u.id}
                      className="flex items-center gap-2 cursor-pointer hover:bg-secondary rounded-lg px-2 py-2 -mx-2 -my-1.5"
                    >
                      <input
                        type="checkbox"
                        checked={assignExecutorIds.includes(u.id)}
                        onChange={() => onExecutorToggle(u.id)}
                        className="w-4 h-4 rounded border-border bg-background accent-accent focus:ring-2 focus:ring-accent cursor-pointer"
                        aria-label={t('workflow.modals.assignExecutorAria', { name: u.full_name })}
                      />
                      <span className="text-sm">{u.full_name}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center px-4 h-10 text-sm font-semibold border border-border bg-card text-foreground rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="button"
              onClick={onAssign}
              disabled={workflowLoading || assignExecutorIds.length === 0}
              className="inline-flex items-center justify-center gap-2 px-4 h-10 text-sm font-semibold bg-accent text-accent-foreground rounded-xl hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {workflowLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
              {t('actions.assign')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={workflowModal === 'complete'} onOpenChange={(open) => !open && onClose()}>
        <DialogContent aria-describedby="complete-description">
          <DialogHeader>
            <DialogTitle>{t('workflow.modals.completeTitle')}</DialogTitle>
            <DialogDescription id="complete-description">{t('workflow.modals.completeDesc')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {errorBlock}
            <div className="space-y-2">
              <label htmlFor="complete-comment" className="text-sm font-medium">
                {t('workflow.modals.commentLabel')}
              </label>
              <textarea
                id="complete-comment"
                value={workflowComment}
                onChange={(e) => onCommentChange(e.target.value)}
                rows={3}
                className="flex w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
                placeholder={t('workflow.modals.commentOptionalPlaceholder')}
                aria-describedby="complete-description"
              />
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center px-4 h-10 text-sm font-semibold border border-border bg-card text-foreground rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="button"
              onClick={onComplete}
              disabled={workflowLoading}
              className="inline-flex items-center justify-center gap-2 px-4 h-10 text-sm font-semibold bg-accent text-accent-foreground rounded-xl hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {workflowLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
              {t('actions.complete')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={workflowModal === 'close'} onOpenChange={(open) => !open && onClose()}>
        <DialogContent aria-describedby="close-ticket-description">
          <DialogHeader>
            <DialogTitle>{t('workflow.modals.closeTitle')}</DialogTitle>
            <DialogDescription id="close-ticket-description">{t('workflow.modals.closeDesc')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {errorBlock}
            <div className="space-y-2">
              <label htmlFor="close-comment" className="text-sm font-medium">
                {t('workflow.modals.commentLabel')}
              </label>
              <textarea
                id="close-comment"
                value={workflowComment}
                onChange={(e) => onCommentChange(e.target.value)}
                rows={3}
                className="flex w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
                placeholder={t('workflow.modals.commentOptionalPlaceholder')}
                aria-describedby="close-ticket-description"
              />
            </div>
          </div>
          <DialogFooter>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center px-4 h-10 text-sm font-semibold border border-border bg-card text-foreground rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="button"
              onClick={onCloseTicket}
              disabled={workflowLoading}
              className="inline-flex items-center justify-center gap-2 px-4 h-10 text-sm font-semibold bg-accent text-accent-foreground rounded-xl hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {workflowLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden />}
              {t('actions.close')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default TicketDetailWorkflowModals;
