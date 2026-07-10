import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Bell, Check } from 'lucide-react';
import {
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  type NotificationItem,
} from '@/api/notifications';
import { cn } from '@/lib/utils';

const POLL_INTERVAL_MS = 60_000;
const LIST_PAGE_SIZE = 15;
const PANEL_WIDTH = 360;
const VIEWPORT_MARGIN = 8;

type PanelPosition = { top: number; left: number; width: number };

const NotificationBell = (): ReactNode => {
  const { t, i18n } = useTranslation('common');
  const navigate = useNavigate();

  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [position, setPosition] = useState<PanelPosition | null>(null);

  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const refreshUnread = useCallback(async (): Promise<void> => {
    const result = await getUnreadCount();
    if (result.ok) setUnread(result.data);
  }, []);

  const loadList = useCallback(async (): Promise<void> => {
    setLoading(true);
    const result = await listNotifications({ page: 1, page_size: LIST_PAGE_SIZE });
    if (result.ok) setItems(result.data.items);
    else setItems([]);
    setLoading(false);
  }, []);

  // Initial fetch + 60s polling for the unread badge.
  useEffect(() => {
    void refreshUnread();
    const timer = window.setInterval(() => {
      void refreshUnread();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refreshUnread]);

  const computePosition = useCallback((): void => {
    const button = buttonRef.current;
    if (!button) return;
    const rect = button.getBoundingClientRect();
    const isMobile = window.innerWidth < 480;
    const width = isMobile
      ? Math.min(PANEL_WIDTH, window.innerWidth - VIEWPORT_MARGIN * 2)
      : PANEL_WIDTH;
    let left = rect.left;
    if (left + width > window.innerWidth - VIEWPORT_MARGIN) {
      left = window.innerWidth - VIEWPORT_MARGIN - width;
    }
    if (left < VIEWPORT_MARGIN) left = VIEWPORT_MARGIN;
    setPosition({ top: rect.bottom + 8, left, width });
  }, []);

  // Recompute panel position while open (scroll / resize).
  useLayoutEffect(() => {
    if (!open) return;
    computePosition();
    const handle = (): void => computePosition();
    window.addEventListener('resize', handle);
    window.addEventListener('scroll', handle, true);
    return () => {
      window.removeEventListener('resize', handle);
      window.removeEventListener('scroll', handle, true);
    };
  }, [open, computePosition]);

  // Close on outside click + Escape while open.
  useEffect(() => {
    if (!open) return;
    const handlePointer = (event: MouseEvent): void => {
      const target = event.target as Node;
      if (buttonRef.current?.contains(target)) return;
      if (panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    const handleKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handlePointer);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handlePointer);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  const handleToggle = useCallback((): void => {
    setOpen((prev) => {
      const next = !prev;
      if (next) {
        void loadList();
        void refreshUnread();
      }
      return next;
    });
  }, [loadList, refreshUnread]);

  const handleMarkAll = useCallback(async (): Promise<void> => {
    const result = await markAllRead();
    if (!result.ok) return;
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnread(0);
  }, []);

  const handleSelect = useCallback(
    async (item: NotificationItem): Promise<void> => {
      const wasUnread = !item.is_read;
      // Optimistically mark as read locally.
      setItems((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, is_read: true } : n))
      );
      if (wasUnread) setUnread((prev) => Math.max(0, prev - 1));

      if (!item.is_read) void markRead(item.id);

      if (item.ticket_id) {
        setOpen(false);
        navigate(`/tickets/${item.ticket_id}`);
      }
    },
    [navigate]
  );

  const relativeTime = useCallback(
    (iso: string): string => {
      if (!iso) return '';
      const then = new Date(iso).getTime();
      if (Number.isNaN(then)) return '';
      const diffMs = Date.now() - then;
      const diffMin = Math.floor(diffMs / 60_000);
      if (diffMin < 1) {
        return t('notifications.time.justNow', { defaultValue: 'только что' });
      }
      if (diffMin < 60) {
        return t('notifications.time.minutesAgo', {
          count: diffMin,
          defaultValue: '{{count}} мин назад',
        });
      }
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) {
        return t('notifications.time.hoursAgo', {
          count: diffHours,
          defaultValue: '{{count}} ч назад',
        });
      }
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) {
        return t('notifications.time.daysAgo', {
          count: diffDays,
          defaultValue: '{{count}} дн назад',
        });
      }
      try {
        return new Date(iso).toLocaleDateString(i18n.language || undefined, {
          day: 'numeric',
          month: 'short',
        });
      } catch {
        return '';
      }
    },
    [t, i18n.language]
  );

  const displayCount = unread > 99 ? '99+' : String(unread);
  const hasUnread = unread > 0;
  const ariaLabel = hasUnread
    ? t('notifications.ariaLabelCount', {
        count: unread,
        defaultValue: 'Уведомления, непрочитанных: {{count}}',
      })
    : t('notifications.ariaLabel', { defaultValue: 'Уведомления' });

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={handleToggle}
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
          open && 'bg-secondary'
        )}
      >
        <Bell className="h-5 w-5" aria-hidden />
        {hasUnread && (
          <span
            aria-hidden
            className="absolute -right-1 -top-1 flex min-w-[18px] items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold leading-[18px] text-accent-foreground tabular-nums shadow-sm"
          >
            {displayCount}
          </span>
        )}
      </button>

      {open &&
        position &&
        createPortal(
          <div
            ref={panelRef}
            role="menu"
            aria-label={t('notifications.title', { defaultValue: 'Уведомления' })}
            style={{
              position: 'fixed',
              top: position.top,
              left: position.left,
              width: position.width,
              maxHeight: 'min(70vh, 520px)',
              zIndex: 200,
            }}
            className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-lg"
          >
            <div className="flex flex-shrink-0 items-center justify-between gap-2 border-b border-border px-4 py-3">
              <span className="font-display text-sm font-medium text-foreground">
                {t('notifications.title', { defaultValue: 'Уведомления' })}
              </span>
              <button
                type="button"
                onClick={() => void handleMarkAll()}
                disabled={!hasUnread}
                className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/10 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:cursor-not-allowed disabled:text-muted-foreground disabled:hover:bg-transparent"
              >
                <Check className="h-3.5 w-3.5" aria-hidden />
                {t('notifications.markAllRead', { defaultValue: 'Прочитать все' })}
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {loading && items.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                  {t('notifications.loading', { defaultValue: 'Загрузка…' })}
                </div>
              ) : items.length === 0 ? (
                <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                  {t('notifications.empty', { defaultValue: 'Нет уведомлений' })}
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {items.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => void handleSelect(item)}
                        className={cn(
                          'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-secondary focus-visible:bg-secondary focus-visible:outline-none',
                          !item.is_read && 'bg-accent/[0.04]'
                        )}
                      >
                        <span className="mt-1.5 flex h-2 w-2 flex-shrink-0 items-center justify-center">
                          {!item.is_read && (
                            <span
                              aria-hidden
                              className="h-2 w-2 rounded-full bg-accent"
                            />
                          )}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span
                            className={cn(
                              'block truncate text-sm text-foreground',
                              !item.is_read && 'font-medium'
                            )}
                          >
                            {item.title}
                          </span>
                          {item.message && (
                            <span className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                              {item.message}
                            </span>
                          )}
                          <span className="mt-1 block text-[11px] text-muted-foreground/80 tabular-nums">
                            {relativeTime(item.created_at)}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>,
          document.body
        )}
    </>
  );
};

export default NotificationBell;
