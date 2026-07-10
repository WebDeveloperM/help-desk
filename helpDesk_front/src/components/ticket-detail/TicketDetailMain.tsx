import { useTranslation } from 'react-i18next';
import type { Ticket } from '@/types/ticket';
import { TicketStatus } from '@/types/ticket';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Calendar, User, Building2, MessageSquare, CheckSquare, Package, AlertCircle } from 'lucide-react';
import { formatDate, formatDateShort } from '@/lib/ticketFormatters';
import { cn } from '@/lib/utils';
import TicketCommentsThread from '@/components/ticket-detail/TicketCommentsThread';

interface TicketDetailMainProps {
  ticket: Ticket;
  effectivePlannedDate: string | null;
  slaBadge: { label: string; className: string } | null;
  progressDraft: number;
  progressError: string | null;
  progressLoading: boolean;
  onProgressChange: (value: number) => void;
  onSaveProgress: () => void;
}

const TicketDetailMain = ({
  ticket,
  effectivePlannedDate,
  slaBadge,
  progressDraft,
  progressError,
  progressLoading,
  onProgressChange,
  onSaveProgress,
}: TicketDetailMainProps) => {
  const { t } = useTranslation('tickets');
  const showProgressForm =
    ticket.status === TicketStatus.ASSIGNED ||
    ticket.status === TicketStatus.IN_PROGRESS ||
    ticket.status === TicketStatus.WAITING_INFO;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Content */}
      <div className="lg:col-span-2 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('detail.sections.description')}</CardTitle>
          </CardHeader>
          <CardContent>
            <CardDescription className="text-[15px] leading-relaxed whitespace-pre-wrap">
              {ticket.description}
            </CardDescription>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5" aria-hidden />
              {t('detail.sections.commentsHistory')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {ticket.approver_comment && (
                <div className="p-4 rounded-xl bg-muted/50 border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-4 h-4 text-muted-foreground" aria-hidden />
                    <span className="text-sm font-medium">{t('detail.sections.approverComment')}</span>
                    {ticket.approved_at && (
                      <span className="text-xs text-muted-foreground ml-auto">
                        {formatDateShort(ticket.approved_at)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground">{ticket.approver_comment}</p>
                </div>
              )}
              {ticket.completion_comment && (
                <div className="p-4 rounded-xl bg-muted/50 border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckSquare className="w-4 h-4 text-muted-foreground" aria-hidden />
                    <span className="text-sm font-medium">{t('detail.sections.completionComment')}</span>
                    {ticket.completed_at && (
                      <span className="text-xs text-muted-foreground ml-auto">
                        {formatDateShort(ticket.completed_at)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground">{ticket.completion_comment}</p>
                </div>
              )}
              {ticket.closed_comment && (
                <div className="p-4 rounded-xl bg-muted/50 border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="w-4 h-4 text-muted-foreground" aria-hidden />
                    <span className="text-sm font-medium">{t('detail.sections.closedComment')}</span>
                    {ticket.closed_at && (
                      <span className="text-xs text-muted-foreground ml-auto">
                        {formatDateShort(ticket.closed_at)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-foreground">{ticket.closed_comment}</p>
                </div>
              )}
              {!ticket.approver_comment && !ticket.completion_comment && !ticket.closed_comment && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  {t('detail.sections.noComments')}
                </p>
              )}
              <TicketCommentsThread ticketId={ticket.id} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sidebar Info */}
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5" aria-hidden />
              {t('detail.sections.dates')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.desiredCompletion')}</div>
              <div className="text-sm font-medium text-foreground">
                {formatDateShort(ticket.desired_completion_date)}
              </div>
            </div>
            {effectivePlannedDate && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.plannedSla')}</div>
                <div className="text-sm font-medium text-foreground">
                  {formatDateShort(effectivePlannedDate)}
                </div>
              </div>
            )}
            {slaBadge && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.slaStatus')}</div>
                <div className={cn('inline-flex rounded-full border px-2.5 py-1 text-xs font-medium', slaBadge.className)}>
                  {slaBadge.label}
                </div>
              </div>
            )}
            {ticket.actual_completion_date && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.actualCompletion')}</div>
                <div className="text-sm font-medium text-foreground">
                  {formatDateShort(ticket.actual_completion_date)}
                </div>
              </div>
            )}
            <div className="pt-2 border-t border-border">
              <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.createdAt')}</div>
              <div className="text-sm font-medium text-foreground">
                {formatDate(ticket.created_at)}
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.updatedAt')}</div>
              <div className="text-sm font-medium text-foreground">
                {formatDate(ticket.updated_at)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" aria-hidden />
              {t('detail.sections.participants')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.creator')}</div>
              <div className="text-sm font-medium text-foreground">
                {ticket.created_by?.full_name || `User ${ticket.created_by_id}`}
              </div>
              {ticket.created_by?.email && (
                <div className="text-xs text-muted-foreground">{ticket.created_by.email}</div>
              )}
            </div>
            {ticket.assigned_department_id && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.assignedDepartment')}</div>
                <div className="text-sm font-medium text-foreground flex items-center gap-2">
                  <Building2 className="w-4 h-4" aria-hidden />
                  {ticket.assigned_department?.name || `Department ${ticket.assigned_department_id}`}
                </div>
              </div>
            )}
            {ticket.approver_user_id && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.approver')}</div>
                <div className="text-sm font-medium text-foreground">
                  {ticket.approver?.full_name || `User ${ticket.approver_user_id}`}
                </div>
              </div>
            )}
            {ticket.completed_by_id && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.completedBy')}</div>
                <div className="text-sm font-medium text-foreground">
                  {ticket.completed_by?.full_name || `User ${ticket.completed_by_id}`}
                </div>
              </div>
            )}
            {ticket.executors && ticket.executors.length > 0 && (
              <div>
                <div className="text-xs font-medium text-muted-foreground mb-1">{t('detail.sections.executors')}</div>
                <ul className="text-sm font-medium text-foreground space-y-1">
                  {ticket.executors.map((ex) => (
                    <li key={ex.id}>{ex.full_name}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        {ticket.ticket_metadata && Object.keys(ticket.ticket_metadata).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>{t('detail.sections.additionalInfo')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                {Object.entries(ticket.ticket_metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-4">
                    <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}:</span>
                    <span className="text-foreground font-medium">{String(value)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {showProgressForm && (
          <Card>
            <CardHeader>
              <CardTitle>{t('detail.sections.updateProgress')}</CardTitle>
              <CardDescription>
                {t('detail.sections.updateProgressDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {progressError && (
                <div
                  role="alert"
                  className="flex items-center gap-2 rounded-xl border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
                  <span>{progressError}</span>
                </div>
              )}
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={progressDraft}
                  onChange={(e) => onProgressChange(Number(e.target.value))}
                  className="w-full accent-accent"
                  aria-label={t('detail.sections.progressInputAria')}
                />
                <span className="w-14 text-right text-sm font-medium text-foreground">
                  {progressDraft}%
                </span>
              </div>
              <button
                type="button"
                onClick={() => void onSaveProgress()}
                disabled={progressLoading || progressDraft === ticket.progress_percent}
                className="inline-flex w-full items-center justify-center rounded-xl bg-accent px-4 h-11 text-sm font-semibold text-accent-foreground hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
              >
                {progressLoading ? t('detail.sections.saving') : t('detail.sections.saveProgress')}
              </button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default TicketDetailMain;
