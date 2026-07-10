import { useState, useMemo, useEffect, useCallback, useRef, type JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { Ticket, KanbanColumnStatus } from '../types/ticket';
import { STATUS_TO_COLUMN_MAP } from '../types/ticket';
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from '@/components/ui/sidebar';
import { ThemeProvider } from '../contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import Sidebar from '../components/dashboard/Sidebar';
import StatCard from '../components/dashboard/StatCard';
import KanbanColumn from '../components/dashboard/KanbanColumn';
import TicketCard from '../components/dashboard/TicketCard';
import SearchBar from '../components/dashboard/SearchBar';
import MobileNav from '../components/dashboard/MobileNav';
import QuickActionFAB from '../components/dashboard/QuickActionFAB';
import {
  ArrowUpDown,
  Filter,
  User,
  Plus,
  Inbox,
  PlayCircle,
  CheckCircle2,
  Layers,
  Loader2,
  AlertCircle,
  ArrowUpRight,
  Check,
  Download,
} from 'lucide-react';
import { listTickets } from '@/api/tickets';
import { getCurrentUser } from '@/api/users';
import NewRequestForm from '../components/dashboard/NewRequestForm';
import FilterPanel, {
  EMPTY_FILTERS,
  countActiveFilters,
  type DashboardFilters,
  type SortKey,
} from '../components/dashboard/FilterPanel';

const SEARCH_DEBOUNCE_MS = 200;
const PRIORITY_ORDER: Record<string, number> = { urgent: 4, high: 3, normal: 2, low: 1 };
const NODE_SERIAL = 'OPS-NODE-7A';

const zeroCount = (_ticket: Ticket): number => 0;

const pad2 = (n: number): string => String(n).padStart(2, '0');

const formatClock = (d: Date): string =>
  `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())} UTC`;

const useDebouncedValue = <T,>(value: T, delayMs: number): T => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
};

type TicketsByColumn = Record<KanbanColumnStatus, Ticket[]>;

const groupTicketsByColumn = (tickets: Ticket[]): TicketsByColumn => {
  const buckets: TicketsByColumn = {
    new: [],
    assigned: [],
    in_progress: [],
    completed: [],
    closed: [],
  };
  for (const ticket of tickets) {
    const column = STATUS_TO_COLUMN_MAP[ticket.status];
    if (column) buckets[column].push(ticket);
  }
  return buckets;
};

const createdDesc = (a: Ticket, b: Ticket): number =>
  new Date(b.created_at).getTime() - new Date(a.created_at).getTime();

const sortTickets = (list: Ticket[], key: SortKey): Ticket[] => {
  const arr = [...list];
  switch (key) {
    case 'oldest':
      arr.sort((a, b) => -createdDesc(a, b));
      break;
    case 'priority':
      arr.sort(
        (a, b) =>
          (PRIORITY_ORDER[b.priority] ?? 0) - (PRIORITY_ORDER[a.priority] ?? 0) ||
          createdDesc(a, b),
      );
      break;
    case 'progress':
      arr.sort((a, b) => b.progress_percent - a.progress_percent || createdDesc(a, b));
      break;
    case 'newest':
    default:
      arr.sort(createdDesc);
      break;
  }
  return arr;
};

const isOverdueTicket = (ticket: Ticket, nowMs: number): boolean => {
  if (ticket.status === 'completed' || ticket.status === 'closed') return false;
  if (!ticket.planned_completion_date) return false;
  return new Date(ticket.planned_completion_date).getTime() < nowMs;
};

const SORT_KEYS: SortKey[] = ['newest', 'oldest', 'priority', 'progress'];

type PresetId = 'all' | 'mine' | 'urgent' | 'overdue' | 'unassigned';

const PRESET_IDS: PresetId[] = ['all', 'mine', 'urgent', 'overdue', 'unassigned'];

const presetFilters = (id: PresetId): DashboardFilters => {
  switch (id) {
    case 'mine':
      return { ...EMPTY_FILTERS, mineOnly: true };
    case 'urgent':
      return { ...EMPTY_FILTERS, urgentOnly: true };
    case 'overdue':
      return { ...EMPTY_FILTERS, overdueOnly: true };
    case 'unassigned':
      return { ...EMPTY_FILTERS, unassignedOnly: true };
    case 'all':
    default:
      return EMPTY_FILTERS;
  }
};

const filtersEqual = (a: DashboardFilters, b: DashboardFilters): boolean => {
  const sameSet = (x: string[], y: string[]): boolean =>
    x.length === y.length && [...x].sort().join('|') === [...y].sort().join('|');
  return (
    sameSet(a.statuses, b.statuses) &&
    sameSet(a.priorities, b.priorities) &&
    sameSet(a.categoryIds, b.categoryIds) &&
    sameSet(a.departmentIds, b.departmentIds) &&
    a.urgentOnly === b.urgentOnly &&
    a.mineOnly === b.mineOnly &&
    a.overdueOnly === b.overdueOnly &&
    a.unassignedOnly === b.unassignedOnly
  );
};

const matchPreset = (filters: DashboardFilters): PresetId | null => {
  for (const id of PRESET_IDS) {
    if (filtersEqual(filters, presetFilters(id))) return id;
  }
  return null;
};

const csvEscape = (value: string | number): string => {
  const str = String(value ?? '');
  if (/["\n\r,;]/.test(str)) return `"${str.replace(/"/g, '""')}"`;
  return str;
};

const triggerCsvDownload = (rows: string[][], filenamePrefix: string): void => {
  const csv = '﻿' + rows.map((row) => row.map(csvEscape).join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${filenamePrefix}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const { t: tCommon } = useTranslation('common');
  const [activeNav, setActiveNav] = useState('Dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isNewRequestFormOpen, setIsNewRequestFormOpen] = useState(false);
  const [filters, setFilters] = useState<DashboardFilters>(EMPTY_FILTERS);
  const [sortKey, setSortKey] = useState<SortKey>('newest');
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const fetchTickets = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setError(tCommon('states.noToken'));
      return;
    }
    setLoading(true);
    setError(null);
    const result = await listTickets({ page_size: 100 });
    if (result.ok) {
      setTickets(result.data.items);
    } else {
      setError(result.error);
    }
    setLoading(false);
  }, [token, tCommon]);

  useEffect(() => {
    void fetchTickets();
  }, [fetchTickets]);

  useEffect(() => {
    let active = true;
    void getCurrentUser().then((res) => {
      if (active && res.ok) setCurrentUserId(res.data.id);
    });
    return () => {
      active = false;
    };
  }, []);

  const debouncedSearchQuery = useDebouncedValue(searchQuery, SEARCH_DEBOUNCE_MS);

  const filteredTickets = useMemo(() => {
    const query = debouncedSearchQuery.trim().toLowerCase();
    const nowMs = Date.now();
    return tickets.filter((ticket) => {
      if (query) {
        const matchesQuery =
          ticket.title.toLowerCase().includes(query) ||
          ticket.description.toLowerCase().includes(query) ||
          ticket.ticket_number.toLowerCase().includes(query);
        if (!matchesQuery) return false;
      }
      if (filters.statuses.length > 0 && !filters.statuses.includes(ticket.status)) return false;
      if (filters.priorities.length > 0 && !filters.priorities.includes(ticket.priority)) return false;
      if (filters.categoryIds.length > 0 && !filters.categoryIds.includes(ticket.category_id)) return false;
      if (
        filters.departmentIds.length > 0 &&
        !filters.departmentIds.includes(ticket.creator_department_id) &&
        !(ticket.assigned_department_id != null && filters.departmentIds.includes(ticket.assigned_department_id))
      )
        return false;
      if (filters.urgentOnly && !ticket.is_urgent) return false;
      if (filters.mineOnly && ticket.created_by_id !== currentUserId) return false;
      if (filters.unassignedOnly && ticket.assigned_department_id != null) return false;
      if (filters.overdueOnly && !isOverdueTicket(ticket, nowMs)) return false;
      return true;
    });
  }, [tickets, debouncedSearchQuery, filters, currentUserId]);

  const sortedTickets = useMemo(
    () => sortTickets(filteredTickets, sortKey),
    [filteredTickets, sortKey],
  );

  const ticketsByColumn = useMemo(() => groupTicketsByColumn(sortedTickets), [sortedTickets]);

  const stats = useMemo(() => {
    const total = filteredTickets.length;
    const completed = ticketsByColumn.completed.length;
    return {
      newCount: ticketsByColumn.new.length,
      inProgressCount: ticketsByColumn.in_progress.length,
      completedCount: completed,
      total,
      successRate: total > 0 ? Math.round((completed / total) * 100) : 0,
    };
  }, [filteredTickets, ticketsByColumn]);

  const activePreset = useMemo(() => matchPreset(filters), [filters]);
  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters]);

  const handleFiltersChange = useCallback((next: DashboardFilters) => {
    setFilters(next);
  }, []);

  const handleResetFilters = useCallback(() => {
    setFilters(EMPTY_FILTERS);
  }, []);

  const handlePresetSelect = useCallback((id: PresetId) => {
    setFilters(presetFilters(id));
  }, []);

  const handleTicketClick = useCallback(
    (ticket: Ticket) => {
      navigate(`/tickets/${ticket.id}`);
    },
    [navigate]
  );

  const handleButtonClick = useCallback((action: string) => {
    if (action === 'add') {
      setIsNewRequestFormOpen(true);
    }
  }, []);

  return (
    <ThemeProvider>
      <SidebarProvider>
        <DashboardContent
          activeNav={activeNav}
          setActiveNav={setActiveNav}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          tickets={tickets}
          loading={loading}
          error={error}
          onRetry={fetchTickets}
          ticketsByColumn={ticketsByColumn}
          handleTicketClick={handleTicketClick}
          handleButtonClick={handleButtonClick}
          allTicketsForMobile={sortedTickets}
          stats={stats}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onResetFilters={handleResetFilters}
          sortKey={sortKey}
          onSortChange={setSortKey}
          activePreset={activePreset}
          onPresetSelect={handlePresetSelect}
          activeFilterCount={activeFilterCount}
        />

        <NewRequestForm
          open={isNewRequestFormOpen}
          onOpenChange={setIsNewRequestFormOpen}
          onSuccess={fetchTickets}
        />
      </SidebarProvider>
    </ThemeProvider>
  );
};

type DashboardStats = {
  newCount: number;
  inProgressCount: number;
  completedCount: number;
  total: number;
  successRate: number;
};

type DashboardContentProps = {
  activeNav: string;
  setActiveNav: (nav: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  tickets: Ticket[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  ticketsByColumn: TicketsByColumn;
  handleTicketClick: (ticket: Ticket) => void;
  handleButtonClick: (action: string) => void;
  allTicketsForMobile: Ticket[];
  stats: DashboardStats;
  filters: DashboardFilters;
  onFiltersChange: (next: DashboardFilters) => void;
  onResetFilters: () => void;
  sortKey: SortKey;
  onSortChange: (key: SortKey) => void;
  activePreset: PresetId | null;
  onPresetSelect: (id: PresetId) => void;
  activeFilterCount: number;
};

const DashboardContent = ({
  activeNav,
  setActiveNav,
  searchQuery,
  setSearchQuery,
  tickets,
  loading,
  error,
  onRetry,
  ticketsByColumn,
  handleTicketClick,
  handleButtonClick,
  allTicketsForMobile,
  stats,
  filters,
  onFiltersChange,
  onResetFilters,
  sortKey,
  onSortChange,
  activePreset,
  onPresetSelect,
  activeFilterCount,
}: DashboardContentProps): JSX.Element => {
  const { open } = useSidebar();
  const { profile } = useAuth();
  const isAdmin = profile?.roles?.includes('admin') ?? false;
  const { t } = useTranslation('dashboard');
  const { t: tCommon } = useTranslation('common');
  const [now, setNow] = useState<Date>(() => new Date());
  const [sortMenuOpen, setSortMenuOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const sortWrapRef = useRef<HTMLDivElement | null>(null);
  const filterWrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!sortMenuOpen && !filterOpen) return;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (sortMenuOpen && sortWrapRef.current && !sortWrapRef.current.contains(target)) {
        setSortMenuOpen(false);
      }
      if (filterOpen && filterWrapRef.current && !filterWrapRef.current.contains(target)) {
        setFilterOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSortMenuOpen(false);
        setFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [sortMenuOpen, filterOpen]);

  const handleExportCsv = useCallback(() => {
    const header = [
      t('export.col.number', { defaultValue: 'Номер' }),
      t('export.col.title', { defaultValue: 'Заголовок' }),
      t('export.col.status', { defaultValue: 'Статус' }),
      t('export.col.priority', { defaultValue: 'Приоритет' }),
      t('export.col.progress', { defaultValue: 'Прогресс %' }),
      t('export.col.creator', { defaultValue: 'Создал' }),
      t('export.col.date', { defaultValue: 'Дата' }),
    ];
    const rows = allTicketsForMobile.map((ticket) => [
      ticket.ticket_number,
      ticket.title,
      t(`filters.status.${ticket.status}`, { defaultValue: ticket.status }),
      t(`filters.priority.${ticket.priority}`, { defaultValue: ticket.priority }),
      String(ticket.progress_percent ?? 0),
      ticket.created_by?.full_name ?? ticket.created_by_id,
      ticket.created_at ? ticket.created_at.slice(0, 10) : '',
    ]);
    triggerCsvDownload([header, ...rows], 'tickets');
  }, [allTicketsForMobile, t]);

  if (loading) {
    return (
      <div
        className="flex min-h-screen w-full items-center justify-center bg-background font-sans"
        role="status"
        aria-live="polite"
        aria-label={t('loading.tickets')}
      >
        <div className="flex flex-col items-center gap-4 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden />
          <p className="text-sm font-medium">
            {t('loading.queue')}
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex min-h-screen w-full items-center justify-center bg-background p-4 font-sans"
        role="alert"
      >
        <div className="flex max-w-md flex-col items-center gap-4 rounded-2xl border border-destructive/40 bg-card p-6 text-center shadow-sm">
          <AlertCircle className="h-10 w-10 text-destructive" aria-hidden />
          <p className="text-[15px] text-foreground">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            aria-label={t('errors.retry')}
          >
            {tCommon('actions.retry')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full bg-background font-sans">
      <div className="hidden md:block">
        <ShadcnSidebar>
          <Sidebar activeNav={activeNav} onNavChange={setActiveNav} />
        </ShadcnSidebar>
      </div>

      <main
        className={cn(
          'min-h-screen w-full overflow-auto pb-20 pt-14 transition-all duration-300 md:pb-6 md:pt-0',
          open
            ? 'md:ml-[300px] md:w-[calc(100vw-300px)]'
            : 'md:ml-[80px] md:w-[calc(100vw-80px)]',
        )}
        aria-label={t('headings.ticketQueue')}
      >
        {/* Top ops strip */}
        <div className="hidden items-center justify-between gap-4 border-b border-border px-6 py-3 text-xs font-medium text-muted-foreground md:flex">
          <span className="flex items-center gap-3">
            <span className="relative inline-flex h-1.5 w-1.5">
              <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-50" aria-hidden />
              <span className="relative h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            </span>
            <span className="text-foreground">{t('topStrip.channel')}</span>
            <span className="text-border">/</span>
            <span>{NODE_SERIAL}</span>
          </span>
          <span className="flex items-center gap-4">
            <span>{t('topStrip.queue')} · {pad2(stats.total)}</span>
            <span className="text-border">/</span>
            <span className="tabular-nums text-foreground">{formatClock(now)}</span>
          </span>
        </div>

        <div className="px-4 pb-6 md:px-6 md:pt-6">
          {/* Page heading */}
          <div className="mb-6 flex flex-col gap-1.5 md:mb-8">
            <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              {t('headings.operations')}
              {isAdmin && (
                <span
                  className="inline-flex items-center gap-1 rounded-full bg-accent/12 px-2.5 py-0.5 text-[11px] font-semibold text-accent"
                  title={t('admin.allTicketsHint', { defaultValue: 'Видны заявки всех отделов' })}
                >
                  {t('admin.allTicketsBadge', { defaultValue: 'Режим администратора' })}
                </span>
              )}
            </span>
            <h1 className="font-display text-[32px] leading-tight tracking-[-0.02em] text-foreground md:text-[44px]">
              {t('headings.ticketQueue')}
            </h1>
          </div>

          {/* Action bar */}
          <div
            className="mb-6 flex flex-col items-stretch gap-3 md:flex-row md:items-center md:gap-4"
            role="search"
            aria-label={t('search.aria')}
          >
            <SearchBar
              placeholder={t('search.placeholder')}
              value={searchQuery}
              onChange={setSearchQuery}
              className="w-full md:max-w-md"
            />
            <div className="flex flex-wrap items-center gap-2 md:gap-3">
              <div className="relative" ref={sortWrapRef}>
                <ToolbarButton
                  onClick={() => {
                    setSortMenuOpen((prev) => !prev);
                    setFilterOpen(false);
                  }}
                  ariaLabel={t('actions.sort')}
                  icon={<ArrowUpDown className="h-3.5 w-3.5" aria-hidden />}
                  label={t('actions.sort')}
                  ariaHasPopup="menu"
                  ariaExpanded={sortMenuOpen}
                />
                {sortMenuOpen && (
                  <ul
                    role="menu"
                    aria-label={t('sort.title', { defaultValue: 'Сортировка' })}
                    className="absolute right-0 z-40 mt-2 w-56 rounded-2xl border border-border bg-card p-1.5 shadow-xl"
                  >
                    {SORT_KEYS.map((key) => {
                      const active = sortKey === key;
                      return (
                        <li key={key} role="none">
                          <button
                            type="button"
                            role="menuitemradio"
                            aria-checked={active}
                            onClick={() => {
                              onSortChange(key);
                              setSortMenuOpen(false);
                            }}
                            className={cn(
                              'flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
                              active
                                ? 'bg-accent/10 text-accent'
                                : 'text-foreground hover:bg-secondary',
                            )}
                          >
                            {t(`sort.${key}`, { defaultValue: key })}
                            {active && <Check className="h-4 w-4" aria-hidden />}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
              <div className="relative" ref={filterWrapRef}>
                <ToolbarButton
                  onClick={() => {
                    setFilterOpen((prev) => !prev);
                    setSortMenuOpen(false);
                  }}
                  ariaLabel={t('actions.filter')}
                  icon={<Filter className="h-3.5 w-3.5" aria-hidden />}
                  label={t('actions.filter')}
                  ariaHasPopup="dialog"
                  ariaExpanded={filterOpen}
                  active={activeFilterCount > 0}
                  badge={activeFilterCount}
                />
                {filterOpen && (
                  <FilterPanel
                    filters={filters}
                    onFiltersChange={onFiltersChange}
                    onReset={onResetFilters}
                    onClose={() => setFilterOpen(false)}
                    showDepartments={isAdmin}
                  />
                )}
              </div>
              <ToolbarButton
                onClick={handleExportCsv}
                ariaLabel={t('export.aria', { defaultValue: 'Экспорт в CSV' })}
                icon={<Download className="h-3.5 w-3.5" aria-hidden />}
                label={t('actions.export', { defaultValue: 'Экспорт' })}
              />
              <button
                type="button"
                className={cn(
                  'inline-flex h-10 w-10 items-center justify-center rounded-xl border transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 md:hidden',
                  filters.mineOnly
                    ? 'border-accent/60 bg-accent/10 text-accent'
                    : 'border-border bg-card text-foreground hover:bg-secondary',
                )}
                onClick={() => onFiltersChange({ ...filters, mineOnly: !filters.mineOnly })}
                aria-label={t('actions.myTickets')}
                aria-pressed={filters.mineOnly}
              >
                <User className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                className="group hidden h-10 items-center justify-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 md:inline-flex"
                onClick={() => handleButtonClick('add')}
                aria-label={t('actions.newRequest')}
              >
                <Plus className="h-4 w-4" aria-hidden />
                {t('actions.newRequest')}
                <ArrowUpRight
                  className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                  aria-hidden
                />
              </button>
            </div>
          </div>

          {/* Stats row */}
          <div
            className="mb-8 grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
            role="region"
            aria-label={t('headings.ticketQueue')}
          >
            <StatCard
              channel="01"
              title={t('stats.new')}
              value={pad2(stats.newCount)}
              hint={t('stats.newHint')}
              icon={Inbox}
            />
            <StatCard
              channel="02"
              title={t('stats.inProgress')}
              value={pad2(stats.inProgressCount)}
              hint={t('stats.inProgressHint')}
              icon={PlayCircle}
              active
            />
            <StatCard
              channel="03"
              title={t('stats.completed')}
              value={pad2(stats.completedCount)}
              hint={t('stats.completedHint', { rate: stats.successRate })}
              icon={CheckCircle2}
            />
            <StatCard
              channel="04"
              title={t('stats.queueTotal')}
              value={pad2(stats.total)}
              hint={t('stats.queueTotalHint')}
              icon={Layers}
            />
          </div>

          {/* Quick-filter presets */}
          <div
            className="mb-6 flex flex-wrap items-center gap-2"
            role="group"
            aria-label={t('presets.aria', { defaultValue: 'Быстрые фильтры' })}
          >
            {PRESET_IDS.map((id) => {
              const active = activePreset === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onPresetSelect(id)}
                  aria-pressed={active}
                  className={cn(
                    'inline-flex h-9 items-center rounded-full border px-4 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
                    active
                      ? 'border-accent bg-accent text-accent-foreground'
                      : 'border-border bg-card text-foreground hover:bg-secondary',
                  )}
                >
                  {t(`presets.${id}`, { defaultValue: id })}
                </button>
              );
            })}
          </div>

          {/* Kanban */}
          <div
            className="-mx-6 hidden overflow-x-auto px-6 pb-4 md:block"
            role="region"
            aria-label={t('kanbanCols.title')}
          >
            {allTicketsForMobile.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-muted/20 py-16 text-center" role="status">
                <p className="text-sm font-medium text-muted-foreground">
                  {tickets.length === 0 ? t('list.noTickets') : t('list.noMatches')}
                </p>
                {tickets.length > 0 && (
                  <p className="mt-2 text-xs text-muted-foreground opacity-70">
                    {t('list.tryFilters')}
                  </p>
                )}
              </div>
            ) : (
              <div className="flex min-w-max gap-4">
                <div className="w-80 flex-shrink-0">
                  <KanbanColumn
                    title={t('kanbanCols.new')}
                    channel="Q1"
                    tickets={ticketsByColumn.new}
                    onTicketClick={handleTicketClick}
                    getCommentsCount={zeroCount}
                    getTasksCount={zeroCount}
                  />
                </div>
                <div className="w-80 flex-shrink-0">
                  <KanbanColumn
                    title={t('kanbanCols.assigned')}
                    channel="Q2"
                    tickets={ticketsByColumn.assigned}
                    onTicketClick={handleTicketClick}
                    getCommentsCount={zeroCount}
                    getTasksCount={zeroCount}
                  />
                </div>
                <div className="w-80 flex-shrink-0">
                  <KanbanColumn
                    title={t('kanbanCols.inProgress')}
                    channel="Q3"
                    active
                    tickets={ticketsByColumn.in_progress}
                    onTicketClick={handleTicketClick}
                    getCommentsCount={zeroCount}
                    getTasksCount={zeroCount}
                  />
                </div>
                <div className="w-80 flex-shrink-0">
                  <KanbanColumn
                    title={t('kanbanCols.completed')}
                    channel="Q4"
                    tickets={ticketsByColumn.completed}
                    onTicketClick={handleTicketClick}
                    getCommentsCount={zeroCount}
                    getTasksCount={zeroCount}
                  />
                </div>
                <div className="w-80 flex-shrink-0">
                  <KanbanColumn
                    title={t('kanbanCols.closed')}
                    channel="Q5"
                    tickets={ticketsByColumn.closed}
                    onTicketClick={handleTicketClick}
                    getCommentsCount={zeroCount}
                    getTasksCount={zeroCount}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Mobile list */}
          <div className="space-y-3 md:hidden" role="region" aria-label={t('list.aria')}>
            {allTicketsForMobile.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-muted/20 px-4 py-12 text-center" role="status">
                <p className="text-sm font-medium text-muted-foreground">
                  {tickets.length === 0 ? t('list.noTickets') : t('list.noMatches')}
                </p>
                {tickets.length > 0 && (
                  <p className="mt-2 text-xs text-muted-foreground opacity-70">
                    {t('list.tryFilters')}
                  </p>
                )}
              </div>
            ) : (
              allTicketsForMobile.map((ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  onClick={() => handleTicketClick(ticket)}
                  commentsCount={0}
                  tasksCount={0}
                />
              ))
            )}
          </div>
        </div>
      </main>

      <MobileNav activeNav={activeNav} onNavChange={setActiveNav} />
      <QuickActionFAB onClick={() => handleButtonClick('add')} />
    </div>
  );
};

type ToolbarButtonProps = {
  onClick: () => void;
  ariaLabel: string;
  icon: JSX.Element;
  label: string;
  badge?: number;
  active?: boolean;
  ariaExpanded?: boolean;
  ariaHasPopup?: 'menu' | 'dialog' | 'listbox' | 'true';
};

const ToolbarButton = ({
  onClick,
  ariaLabel,
  icon,
  label,
  badge,
  active,
  ariaExpanded,
  ariaHasPopup,
}: ToolbarButtonProps) => (
  <button
    type="button"
    onClick={onClick}
    aria-label={ariaLabel}
    aria-expanded={ariaExpanded}
    aria-haspopup={ariaHasPopup}
    className={cn(
      'relative inline-flex h-10 items-center gap-2 rounded-xl border px-3.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 md:px-4',
      active
        ? 'border-accent/60 bg-accent/10 text-accent'
        : 'border-border bg-card text-foreground hover:bg-secondary',
    )}
  >
    {icon}
    <span className="hidden sm:inline">{label}</span>
    {badge !== undefined && badge > 0 && (
      <span className="ml-0.5 inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-accent px-1 text-[11px] font-semibold tabular-nums text-accent-foreground">
        {badge}
      </span>
    )}
  </button>
);

export default Dashboard;
