import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from '@/components/ui/sidebar';
import { ThemeProvider } from '../contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import Sidebar from '../components/dashboard/Sidebar';
import { Card, CardContent } from '@/components/ui/card';
import type { Ticket } from '@/types/ticket';
import { getSlaBadge } from '@/lib/ticketFormatters';
import { AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  getTicketById,
  approveTicket,
  rejectTicket,
  assignTicket,
  startProgressTicket,
  waitingInfoTicket,
  completeTicket,
  closeTicket,
  updateTicketProgress,
} from '@/api/tickets';
import { listUsersByDepartment } from '@/api/departments';
import TicketDetailHeader from '@/components/ticket-detail/TicketDetailHeader';
import TicketDetailActions from '@/components/ticket-detail/TicketDetailActions';
import TicketDetailMain from '@/components/ticket-detail/TicketDetailMain';
import TicketDetailWorkflowModals from '@/components/ticket-detail/TicketDetailWorkflowModals';

const isAbortError = (err: unknown): boolean =>
  err instanceof DOMException && err.name === 'AbortError';

const TicketDetailContent = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token } = useAuth();
  const { open } = useSidebar();
  const { t } = useTranslation('tickets');
  const { t: tCommon } = useTranslation('common');
  const [activeNav] = useState('Dashboard');
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowModal, setWorkflowModal] = useState<'approve' | 'reject' | 'assign' | 'complete' | 'close' | null>(null);
  const [workflowComment, setWorkflowComment] = useState('');
  const [assignExecutorIds, setAssignExecutorIds] = useState<string[]>([]);
  const [assignUsers, setAssignUsers] = useState<{ id: string; full_name: string; email: string }[]>([]);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [progressDraft, setProgressDraft] = useState<number>(0);
  const [progressLoading, setProgressLoading] = useState(false);
  const [progressError, setProgressError] = useState<string | null>(null);

  const fetchTicket = useCallback(
    async (signal?: AbortSignal) => {
      if (!id) {
        setLoading(false);
        setError(t('detail.noTicketId'));
        return;
      }
      if (!token) {
        setLoading(false);
        setError(tCommon('states.noToken'));
        return;
      }
      setLoading(true);
      setError(null);
      const result = await getTicketById(id, { signal });
      if (signal?.aborted) return;
      if (result.ok) {
        setTicket(result.data);
      } else {
        setError(result.error);
        setTicket(null);
      }
      setLoading(false);
    },
    [id, token, t, tCommon]
  );

  useEffect(() => {
    const controller = new AbortController();
    void fetchTicket(controller.signal).catch((err) => {
      if (!isAbortError(err)) throw err;
    });
    return () => controller.abort();
  }, [fetchTicket]);

  useEffect(() => {
    if (!token || workflowModal !== 'assign' || !ticket?.creator_department_id) {
      setAssignUsers([]);
      return;
    }
    const controller = new AbortController();
    const loadUsers = async () => {
      const result = await listUsersByDepartment(ticket.creator_department_id, { signal: controller.signal });
      if (controller.signal.aborted) return;
      if (result.ok) setAssignUsers(result.data);
      else setAssignUsers([]);
      setAssignExecutorIds([]);
    };
    void loadUsers().catch((err) => {
      if (!isAbortError(err)) throw err;
    });
    return () => controller.abort();
  }, [token, workflowModal, ticket?.creator_department_id]);

  useEffect(() => {
    if (!ticket) return;
    setProgressDraft(ticket.progress_percent ?? 0);
    setProgressError(null);
  }, [ticket]);

  const refetchTicket = useCallback(() => {
    void fetchTicket();
  }, [fetchTicket]);

  const handleWorkflowSuccess = useCallback(() => {
    setWorkflowModal(null);
    setWorkflowComment('');
    setAssignExecutorIds([]);
    setWorkflowError(null);
    refetchTicket();
  }, [refetchTicket]);

  const handleApprove = useCallback(async () => {
    if (!token || !id) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await approveTicket(id, workflowComment || undefined);
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, workflowComment, handleWorkflowSuccess]);

  const handleReject = useCallback(async () => {
    if (!token || !id || !workflowComment.trim()) {
      setWorkflowError(t('workflow.errors.rejectReasonRequired'));
      return;
    }
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await rejectTicket(id, workflowComment.trim());
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, workflowComment, handleWorkflowSuccess, t]);

  const handleAssign = useCallback(async () => {
    if (!token || !id || !ticket?.creator_department_id) {
      setWorkflowError(t('workflow.errors.departmentNotFound'));
      return;
    }
    if (assignExecutorIds.length === 0) {
      setWorkflowError(t('workflow.errors.selectAtLeastOneExecutor'));
      return;
    }
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await assignTicket(id, {
      department_id: ticket.creator_department_id,
      executor_user_ids: assignExecutorIds,
    });
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, ticket, assignExecutorIds, handleWorkflowSuccess, t]);

  const handleStartProgress = useCallback(async () => {
    if (!token || !id) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await startProgressTicket(id);
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, handleWorkflowSuccess]);

  const handleComplete = useCallback(async () => {
    if (!token || !id) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await completeTicket(id, workflowComment || undefined);
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, workflowComment, handleWorkflowSuccess]);

  const handleWaitingInfo = useCallback(async () => {
    if (!token || !id) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await waitingInfoTicket(id);
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, handleWorkflowSuccess]);

  const handleCloseTicket = useCallback(async () => {
    if (!token || !id) return;
    setWorkflowLoading(true);
    setWorkflowError(null);
    const result = await closeTicket(id, workflowComment || undefined);
    setWorkflowLoading(false);
    if (result.ok) handleWorkflowSuccess();
    else setWorkflowError(result.error);
  }, [token, id, workflowComment, handleWorkflowSuccess]);

  const handleExecutorToggle = useCallback((userId: string) => {
    setAssignExecutorIds((prev) =>
      prev.includes(userId) ? prev.filter((existing) => existing !== userId) : [...prev, userId]
    );
  }, []);

  const handleSaveProgress = useCallback(async () => {
    if (!token || !id || !ticket) return;
    const normalizedProgress = Math.max(0, Math.min(100, Math.round(progressDraft)));
    if (normalizedProgress === ticket.progress_percent) return;
    setProgressLoading(true);
    setProgressError(null);
    const result = await updateTicketProgress(id, normalizedProgress);
    setProgressLoading(false);
    if (result.ok) {
      setTicket(result.data);
      return;
    }
    setProgressError(result.error);
  }, [token, id, ticket, progressDraft]);

  const mainClassName = cn(
    'p-4 md:p-6 overflow-auto transition-all duration-300 pt-14 md:pt-6 min-h-screen pb-20 md:pb-6 w-full',
    open
      ? 'md:w-[calc(100vw-300px)] md:ml-[300px]'
      : 'md:w-[calc(100vw-80px)] md:ml-[80px]'
  );

  if (loading) {
    return (
      <ThemeProvider>
        <SidebarProvider>
          <div className="flex min-h-screen bg-background font-sans w-full items-center justify-center" role="status" aria-live="polite" aria-label={t('detail.loadingAria')}>
            <div className="flex flex-col items-center gap-4 text-muted-foreground">
              <Loader2 className="h-10 w-10 animate-spin" aria-hidden />
              <p>{t('detail.loading')}</p>
            </div>
          </div>
        </SidebarProvider>
      </ThemeProvider>
    );
  }

  if (error || !ticket) {
    return (
      <ThemeProvider>
        <SidebarProvider>
          <div className="flex min-h-screen bg-background font-sans w-full">
            <div className="hidden md:block">
              <ShadcnSidebar>
                <Sidebar activeNav={activeNav} onNavChange={() => {}} />
              </ShadcnSidebar>
            </div>
            <main
              className={mainClassName}
              aria-label={t('detail.mainAria')}
            >
              <div className="max-w-4xl mx-auto">
                <Card className="rounded-2xl shadow-sm">
                  <CardContent className="p-6 md:p-8 text-center">
                    {error ? (
                      <>
                        <AlertCircle className="mx-auto mb-4 h-12 w-12 text-destructive" aria-hidden />
                        <p className="text-muted-foreground mb-4 text-[15px]">{error}</p>
                        <button
                          type="button"
                          onClick={refetchTicket}
                          className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 h-11 font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                          aria-label={t('detail.retryAria')}
                        >
                          {t('detail.retry')}
                        </button>
                      </>
                    ) : (
                      <p className="text-muted-foreground text-[15px]">{t('detail.notFound')}</p>
                    )}
                    <button
                      type="button"
                      onClick={() => navigate('/dashboard')}
                      className="mt-4 block w-full text-sm font-medium text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
                      aria-label={t('detail.back')}
                    >
                      {t('detail.back')}
                    </button>
                  </CardContent>
                </Card>
              </div>
            </main>
          </div>
        </SidebarProvider>
      </ThemeProvider>
    );
  }

  const slaBadge = getSlaBadge(ticket.sla?.status);
  const effectivePlannedDate =
    ticket.sla?.planned_completion_date ?? ticket.planned_completion_date;

  return (
    <div className="flex min-h-screen bg-background font-sans w-full">
      <div className="hidden md:block">
        <ShadcnSidebar>
          <Sidebar activeNav={activeNav} onNavChange={() => {}} />
        </ShadcnSidebar>
      </div>

      <main
        className={mainClassName}
        aria-label={t('detail.mainAria')}
      >
        <div className="max-w-6xl mx-auto">
          <TicketDetailHeader ticket={ticket} onBack={() => navigate('/dashboard')} />
          <div className="mb-6">
            <TicketDetailActions
              ticket={ticket}
              workflowLoading={workflowLoading}
              onOpenModal={setWorkflowModal}
              onStartProgress={handleStartProgress}
              onWaitingInfo={handleWaitingInfo}
            />
          </div>

          <TicketDetailMain
            ticket={ticket}
            effectivePlannedDate={effectivePlannedDate}
            slaBadge={slaBadge}
            progressDraft={progressDraft}
            progressError={progressError}
            progressLoading={progressLoading}
            onProgressChange={setProgressDraft}
            onSaveProgress={handleSaveProgress}
          />
        </div>

        <TicketDetailWorkflowModals
          workflowModal={workflowModal}
          onClose={() => setWorkflowModal(null)}
          workflowComment={workflowComment}
          onCommentChange={setWorkflowComment}
          workflowError={workflowError}
          workflowLoading={workflowLoading}
          assignExecutorIds={assignExecutorIds}
          assignUsers={assignUsers}
          onExecutorToggle={handleExecutorToggle}
          ticket={ticket}
          onApprove={handleApprove}
          onReject={handleReject}
          onAssign={handleAssign}
          onComplete={handleComplete}
          onCloseTicket={handleCloseTicket}
        />
      </main>
    </div>
  );
};

const TicketDetail = () => {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <TicketDetailContent />
      </SidebarProvider>
    </ThemeProvider>
  );
};

export default TicketDetail;
