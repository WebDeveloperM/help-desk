import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { createTicketComment, getTicketComments } from '@/api/tickets';
import type { TicketComment } from '@/types/ticket';
import { formatDateShort } from '@/lib/ticketFormatters';
import { Loader2, Send } from 'lucide-react';

interface TicketCommentsThreadProps {
  ticketId: string;
}

const TicketCommentsThread = ({ ticketId }: TicketCommentsThreadProps) => {
  const { token } = useAuth();
  const [items, setItems] = useState<TicketComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadComments = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setLoadError('Нет токена авторизации');
      return;
    }
    setLoading(true);
    setLoadError(null);
    const result = await getTicketComments(token, ticketId, 1, 100);
    if (result.ok) {
      setItems(result.data.items);
    } else {
      setLoadError(result.error);
      setItems([]);
    }
    setLoading(false);
  }, [token, ticketId]);

  useEffect(() => {
    void loadComments();
  }, [loadComments]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const text = draft.trim();
    if (!token || !text) return;
    setSubmitting(true);
    setSubmitError(null);
    const result = await createTicketComment(token, ticketId, text);
    setSubmitting(false);
    if (result.ok) {
      setDraft('');
      setItems((prev) => [...prev, result.data]);
      return;
    }
    setSubmitError(result.error);
  };

  if (!token) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Войдите, чтобы видеть и оставлять комментарии.
      </p>
    );
  }

  return (
    <div className="space-y-4 pt-4 border-t border-border">
      <div className="text-sm font-medium text-foreground">Обсуждение</div>
      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status" aria-live="polite">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" aria-hidden />
          Загрузка комментариев…
        </div>
      )}
      {loadError && !loading && (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-xl border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:flex-row sm:items-center sm:justify-between"
        >
          <span>{loadError}</span>
          <button
            type="button"
            onClick={() => void loadComments()}
            className="shrink-0 rounded-lg border border-destructive/40 bg-background px-2.5 py-1 text-xs font-medium text-destructive hover:bg-destructive/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Повторить
          </button>
        </div>
      )}
      {!loading && !loadError && items.length === 0 && (
        <p className="text-sm text-muted-foreground">Сообщений в обсуждении пока нет.</p>
      )}
      {items.length > 0 && (
        <ul className="space-y-3" aria-label="Комментарии к заявке">
          {items.map((c) => (
            <li
              key={c.id}
              className="rounded-xl border border-border bg-muted/30 px-3.5 py-3 text-sm"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
                <span className="font-medium text-foreground">{c.author_full_name}</span>
                <time className="text-xs text-muted-foreground" dateTime={c.created_at}>
                  {formatDateShort(c.created_at)}
                </time>
              </div>
              <p className="text-foreground whitespace-pre-wrap">{c.body}</p>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-2">
        {submitError && (
          <div
            role="alert"
            className="rounded-xl border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {submitError}
          </div>
        )}
        <label htmlFor={`ticket-comment-${ticketId}`} className="sr-only">
          Новый комментарий
        </label>
        <textarea
          id={`ticket-comment-${ticketId}`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="Написать комментарий…"
          className="w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/15"
          disabled={submitting || loading}
          aria-label="Текст комментария"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={submitting || !draft.trim() || loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 h-11 text-sm font-semibold text-accent-foreground hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Отправка…
              </>
            ) : (
              <>
                <Send className="h-4 w-4" aria-hidden />
                Отправить
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default TicketCommentsThread;
