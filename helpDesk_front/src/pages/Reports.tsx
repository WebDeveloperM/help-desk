import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from '@/components/ui/sidebar';
import { ThemeProvider } from '../contexts/ThemeContext';
import { cn } from '@/lib/utils';
import Sidebar from '../components/dashboard/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { getTicketStats, type TicketStats } from '@/api/reports';
import {
  FileText,
  FolderOpen,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Timer,
  ShieldCheck,
  Loader2,
  RotateCw,
  Download,
  Printer,
  BarChart3,
} from 'lucide-react';

type LoadState = 'loading' | 'error' | 'ready';

// Semantic tone for a chart bar -> a token color class.
type Tone = 'accent' | 'neutral' | 'muted' | 'warning' | 'destructive';

const TONE_STYLE: Record<Tone, string> = {
  accent: 'bg-accent',
  neutral: 'bg-muted-foreground/60',
  muted: 'bg-muted-foreground/30',
  warning: 'bg-[#f59e0b]',
  destructive: 'bg-destructive',
};

const statusTone = (status: string): Tone => {
  if (status === 'completed' || status === 'closed' || status === 'approved') return 'accent';
  if (status === 'rejected') return 'destructive';
  if (status === 'in_progress' || status === 'assigned') return 'neutral';
  return 'muted';
};

const priorityTone = (priority: string): Tone => {
  if (priority === 'urgent') return 'destructive';
  if (priority === 'high') return 'warning';
  if (priority === 'normal') return 'accent';
  return 'muted';
};

const ReportsContent = () => {
  const { open } = useSidebar();
  const { t } = useTranslation('reports');
  const [isDesktop, setIsDesktop] = useState(false);
  const [activeNav] = useState('Reports');

  const [state, setState] = useState<LoadState>('loading');
  const [error, setError] = useState<string>('');
  const [stats, setStats] = useState<TicketStats | null>(null);

  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 768);
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);

  const loadStats = useCallback(async (signal?: AbortSignal) => {
    setState('loading');
    setError('');
    const res = await getTicketStats({ signal });
    if (signal?.aborted) return;
    if (!res.ok) {
      setError(res.error);
      setState('error');
      return;
    }
    setStats(res.data);
    setState('ready');
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadStats(controller.signal);
    return () => controller.abort();
  }, [loadStats]);

  const statusLabel = useCallback(
    (status: string): string => t(`statuses.${status}`, { defaultValue: status }),
    [t]
  );
  const priorityLabel = useCallback(
    (priority: string): string => t(`priorities.${priority}`, { defaultValue: priority }),
    [t]
  );

  const handleExportCsv = useCallback(() => {
    if (!stats) return;
    const rows: Array<[string, string | number]> = [
      [t('metric.metric', { defaultValue: 'Метрика' }), t('metric.value', { defaultValue: 'Значение' })],
      [t('kpi.total', { defaultValue: 'Всего заявок' }), stats.total],
      [t('kpi.open', { defaultValue: 'Открыто' }), stats.open],
      [t('kpi.inProgress', { defaultValue: 'В работе' }), stats.in_progress],
      [t('kpi.completed', { defaultValue: 'Выполнено' }), stats.completed],
      [t('kpi.closed', { defaultValue: 'Закрыто' }), stats.closed],
      [t('kpi.overdue', { defaultValue: 'Просрочено' }), stats.overdue],
      [t('kpi.urgentOpen', { defaultValue: 'Срочные в работе' }), stats.urgent_open],
      [t('kpi.createdLast7d', { defaultValue: 'Создано за 7 дней' }), stats.created_last_7d],
      [t('kpi.completedLast7d', { defaultValue: 'Выполнено за 7 дней' }), stats.completed_last_7d],
      [
        t('kpi.avgResolution', { defaultValue: 'Средн. время решения (ч)' }),
        stats.avg_resolution_hours ?? '',
      ],
      [
        t('kpi.slaCompliance', { defaultValue: 'SLA соблюдение (%)' }),
        stats.sla_compliance_pct ?? '',
      ],
    ];

    rows.push(['', '']);
    rows.push([t('charts.byStatus', { defaultValue: 'Заявки по статусам' }), '']);
    stats.by_status.forEach((s) => rows.push([statusLabel(s.status), s.count]));

    rows.push(['', '']);
    rows.push([t('charts.byPriority', { defaultValue: 'Заявки по приоритетам' }), '']);
    stats.by_priority.forEach((p) => rows.push([priorityLabel(p.priority), p.count]));

    rows.push(['', '']);
    rows.push([t('charts.byCategory', { defaultValue: 'Топ категорий' }), '']);
    stats.by_category.forEach((c) => rows.push([c.name, c.count]));

    const escape = (value: string | number): string => {
      const str = String(value);
      return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
    };
    const csv = rows.map((r) => r.map(escape).join(',')).join('\n');
    // Prepend BOM so Excel reads Cyrillic correctly.
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `helpdesk-report-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [stats, t, statusLabel, priorityLabel]);

  const handlePrint = useCallback(() => window.print(), []);

  return (
    <div className="flex min-h-screen bg-background font-sans w-full">
      {/* Sidebar - Desktop only */}
      <div className="hidden md:block print:hidden">
        <ShadcnSidebar>
          <Sidebar activeNav={activeNav} onNavChange={() => {}} />
        </ShadcnSidebar>
      </div>

      {/* Main Content */}
      <main
        className={cn(
          'p-4 md:p-6 overflow-auto transition-all duration-300 pt-14 md:pt-6 min-h-screen pb-20 md:pb-6'
        )}
        style={{
          width: isDesktop ? `calc(100vw - ${open ? '300px' : '80px'})` : '100%',
          marginLeft: isDesktop ? (open ? '300px' : '80px') : '0',
        }}
        aria-label={t('page.aria')}
      >
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="font-display text-3xl font-bold text-foreground mb-2" id="reports-heading">
                {t('page.title')}
              </h1>
              <p className="text-[15px] text-muted-foreground" id="reports-description">
                {t('page.description')}
              </p>
            </div>
            {state === 'ready' && (
              <div className="flex flex-wrap items-center gap-2 print:hidden">
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="inline-flex items-center justify-center gap-2 h-11 md:h-10 px-4 text-sm font-semibold rounded-xl bg-accent text-accent-foreground hover:opacity-90 transition-opacity focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                  aria-label={t('actions.exportCsvAria', { defaultValue: 'Экспортировать отчёт в CSV' })}
                >
                  <Download className="h-4 w-4" aria-hidden />
                  {t('actions.exportCsv', { defaultValue: 'Экспорт CSV' })}
                </button>
                <button
                  type="button"
                  onClick={handlePrint}
                  className="inline-flex items-center justify-center gap-2 h-11 md:h-10 px-4 text-sm font-semibold rounded-xl border border-border bg-card hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                  aria-label={t('actions.printAria', { defaultValue: 'Распечатать отчёт' })}
                >
                  <Printer className="h-4 w-4" aria-hidden />
                  {t('actions.print', { defaultValue: 'Печать' })}
                </button>
              </div>
            )}
          </div>

          {state === 'loading' && (
            <div
              className="flex flex-col items-center justify-center py-24 text-muted-foreground"
              role="status"
              aria-live="polite"
            >
              <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden />
              <p className="mt-3 text-sm">{t('state.loading', { defaultValue: 'Загрузка аналитики…' })}</p>
            </div>
          )}

          {state === 'error' && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <div className="p-3 rounded-full bg-destructive/10 text-destructive" aria-hidden>
                  <AlertTriangle className="h-6 w-6" />
                </div>
                <div>
                  <p className="font-medium text-foreground">
                    {t('state.errorTitle', { defaultValue: 'Не удалось загрузить аналитику' })}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{error}</p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadStats()}
                  className="inline-flex items-center justify-center gap-2 h-11 md:h-10 px-4 text-sm font-semibold rounded-xl bg-accent text-accent-foreground hover:opacity-90 transition-opacity focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                  aria-label={t('state.retry', { defaultValue: 'Повторить' })}
                >
                  <RotateCw className="h-4 w-4" aria-hidden />
                  {t('state.retry', { defaultValue: 'Повторить' })}
                </button>
              </CardContent>
            </Card>
          )}

          {state === 'ready' && stats && (stats.total === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <div className="p-3 rounded-full bg-muted text-muted-foreground" aria-hidden>
                  <BarChart3 className="h-6 w-6" />
                </div>
                <p className="font-medium text-foreground">
                  {t('state.emptyTitle', { defaultValue: 'Пока нет данных' })}
                </p>
                <p className="max-w-md text-sm text-muted-foreground">
                  {t('state.emptyDescription', {
                    defaultValue: 'Аналитика появится, как только в системе будут заявки.',
                  })}
                </p>
              </CardContent>
            </Card>
          ) : (
            <ReportsBody
              stats={stats}
              statusLabel={statusLabel}
              priorityLabel={priorityLabel}
            />
          ))}
        </div>
      </main>
    </div>
  );
};

type KpiProps = {
  title: string;
  value: string;
  icon: typeof FileText;
  hint?: string;
  danger?: boolean;
};

const KpiCard = ({ title, value, icon: Icon, hint, danger }: KpiProps) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      <Icon
        className={cn('h-4 w-4', danger ? 'text-destructive' : 'text-muted-foreground')}
        aria-hidden
      />
    </CardHeader>
    <CardContent>
      <div
        className={cn(
          'font-display text-3xl font-bold tabular-nums',
          danger ? 'text-destructive' : 'text-foreground'
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </CardContent>
  </Card>
);

type BarRow = { label: string; count: number; tone: Tone };

const BarList = ({ rows, emptyLabel }: { rows: BarRow[]; emptyLabel: string }) => {
  const max = Math.max(1, ...rows.map((r) => r.count));
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <li key={row.label} className="flex items-center gap-3">
          <span className="w-28 shrink-0 truncate text-sm text-foreground sm:w-36" title={row.label}>
            {row.label}
          </span>
          <div
            className="relative h-6 flex-1 overflow-hidden rounded-full bg-muted"
            role="img"
            aria-label={`${row.label}: ${row.count}`}
          >
            <div
              className={cn('h-full rounded-full transition-all', TONE_STYLE[row.tone])}
              style={{ width: `${Math.max(4, (row.count / max) * 100)}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right text-sm font-semibold tabular-nums text-foreground">
            {row.count}
          </span>
        </li>
      ))}
    </ul>
  );
};

type ReportsBodyProps = {
  stats: TicketStats;
  statusLabel: (status: string) => string;
  priorityLabel: (priority: string) => string;
};

const ReportsBody = ({ stats, statusLabel, priorityLabel }: ReportsBodyProps) => {
  const { t } = useTranslation('reports');

  const fmtHours = (h: number | null): string =>
    h == null ? '—' : `${Number.isInteger(h) ? h : h.toFixed(1)}${t('unit.hours', { defaultValue: 'ч' })}`;
  const fmtPct = (p: number | null): string =>
    p == null ? '—' : `${Number.isInteger(p) ? p : p.toFixed(1)}%`;

  const statusRows: BarRow[] = useMemo(
    () =>
      [...stats.by_status]
        .sort((a, b) => b.count - a.count)
        .map((s) => ({ label: statusLabel(s.status), count: s.count, tone: statusTone(s.status) })),
    [stats.by_status, statusLabel]
  );

  const priorityOrder = ['urgent', 'high', 'normal', 'low'];
  const priorityRows: BarRow[] = useMemo(
    () =>
      [...stats.by_priority]
        .sort((a, b) => priorityOrder.indexOf(a.priority) - priorityOrder.indexOf(b.priority))
        .map((p) => ({
          label: priorityLabel(p.priority),
          count: p.count,
          tone: priorityTone(p.priority),
        })),
    [stats.by_priority, priorityLabel]
  );

  const categoryRows: BarRow[] = useMemo(
    () =>
      [...stats.by_category]
        .sort((a, b) => b.count - a.count)
        .slice(0, 8)
        .map((c) => ({ label: c.name, count: c.count, tone: 'accent' as Tone })),
    [stats.by_category]
  );

  return (
    <div className="space-y-6">
      {/* KPI Grid */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        role="region"
        aria-label={t('kpi.region', { defaultValue: 'Ключевые показатели' })}
      >
        <KpiCard
          title={t('kpi.total', { defaultValue: 'Всего заявок' })}
          value={String(stats.total)}
          icon={FileText}
          hint={t('kpi.createdLast7dHint', {
            defaultValue: '+{{count}} за 7 дней',
            count: stats.created_last_7d,
          })}
        />
        <KpiCard
          title={t('kpi.open', { defaultValue: 'Открыто' })}
          value={String(stats.open)}
          icon={FolderOpen}
        />
        <KpiCard
          title={t('kpi.completed', { defaultValue: 'Выполнено' })}
          value={String(stats.completed)}
          icon={CheckCircle2}
          hint={t('kpi.completedLast7dHint', {
            defaultValue: '+{{count}} за 7 дней',
            count: stats.completed_last_7d,
          })}
        />
        <KpiCard
          title={t('kpi.overdue', { defaultValue: 'Просрочено' })}
          value={String(stats.overdue)}
          icon={AlertTriangle}
          danger={stats.overdue > 0}
        />
        <KpiCard
          title={t('kpi.urgentOpen', { defaultValue: 'Срочные в работе' })}
          value={String(stats.urgent_open)}
          icon={Flame}
          danger={stats.urgent_open > 0}
        />
        <KpiCard
          title={t('kpi.avgResolution', { defaultValue: 'Средн. время решения' })}
          value={fmtHours(stats.avg_resolution_hours)}
          icon={Timer}
        />
        <KpiCard
          title={t('kpi.slaCompliance', { defaultValue: 'SLA соблюдение' })}
          value={fmtPct(stats.sla_compliance_pct)}
          icon={ShieldCheck}
        />
        <KpiCard
          title={t('kpi.inProgress', { defaultValue: 'В работе' })}
          value={String(stats.in_progress)}
          icon={Loader2}
        />
      </div>

      {/* Throughput */}
      <Card>
        <CardHeader>
          <CardTitle>{t('charts.throughput', { defaultValue: 'Динамика за 14 дней' })}</CardTitle>
          <CardDescription>
            {t('charts.throughputDescription', {
              defaultValue: 'Создано и выполнено заявок по дням',
            })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ThroughputChart points={stats.throughput} />
        </CardContent>
      </Card>

      {/* Status + Priority */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('charts.byStatus', { defaultValue: 'Заявки по статусам' })}</CardTitle>
          </CardHeader>
          <CardContent>
            <BarList
              rows={statusRows}
              emptyLabel={t('charts.noData', { defaultValue: 'Нет данных' })}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('charts.byPriority', { defaultValue: 'Заявки по приоритетам' })}</CardTitle>
          </CardHeader>
          <CardContent>
            <BarList
              rows={priorityRows}
              emptyLabel={t('charts.noData', { defaultValue: 'Нет данных' })}
            />
          </CardContent>
        </Card>
      </div>

      {/* Categories */}
      <Card>
        <CardHeader>
          <CardTitle>{t('charts.byCategory', { defaultValue: 'Топ категорий' })}</CardTitle>
        </CardHeader>
        <CardContent>
          <BarList
            rows={categoryRows}
            emptyLabel={t('charts.noData', { defaultValue: 'Нет данных' })}
          />
        </CardContent>
      </Card>
    </div>
  );
};

const ThroughputChart = ({ points }: { points: TicketStats['throughput'] }) => {
  const { t } = useTranslation('reports');

  if (points.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        {t('charts.noData', { defaultValue: 'Нет данных' })}
      </p>
    );
  }

  const max = Math.max(1, ...points.map((p) => Math.max(p.created, p.completed)));
  // Layout in an intrinsic viewBox; SVG scales responsively.
  const barGroupWidth = 40;
  const width = points.length * barGroupWidth;
  const height = 180;
  const chartH = height - 28; // leave room for date labels
  const gap = 4;
  const barW = (barGroupWidth - gap * 3) / 2;

  const shortDate = (iso: string): string => {
    const parts = iso.split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}` : iso;
  };

  return (
    <div>
      <div className="mb-3 flex items-center gap-4 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-accent" aria-hidden />
          {t('charts.created', { defaultValue: 'Создано' })}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-muted-foreground/60" aria-hidden />
          {t('charts.completed', { defaultValue: 'Выполнено' })}
        </span>
      </div>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={height}
          preserveAspectRatio="xMidYMid meet"
          className="min-w-[560px]"
          role="img"
          aria-label={t('charts.throughputDescription', {
            defaultValue: 'Создано и выполнено заявок по дням',
          })}
        >
          {points.map((p, i) => {
            const x = i * barGroupWidth;
            const createdH = (p.created / max) * chartH;
            const completedH = (p.completed / max) * chartH;
            return (
              <g key={p.date}>
                <rect
                  x={x + gap}
                  y={chartH - createdH}
                  width={barW}
                  height={createdH}
                  rx={2}
                  className="fill-accent"
                >
                  <title>{`${p.date} · ${t('charts.created', { defaultValue: 'Создано' })}: ${p.created}`}</title>
                </rect>
                <rect
                  x={x + gap * 2 + barW}
                  y={chartH - completedH}
                  width={barW}
                  height={completedH}
                  rx={2}
                  className="fill-muted-foreground/60"
                >
                  <title>{`${p.date} · ${t('charts.completed', { defaultValue: 'Выполнено' })}: ${p.completed}`}</title>
                </rect>
                <text
                  x={x + barGroupWidth / 2}
                  y={height - 8}
                  textAnchor="middle"
                  className="fill-muted-foreground"
                  style={{ fontSize: '9px' }}
                >
                  {shortDate(p.date)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

const Reports = () => {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <ReportsContent />
      </SidebarProvider>
    </ThemeProvider>
  );
};

export default Reports;
