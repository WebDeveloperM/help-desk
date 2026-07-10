import { useEffect, useState, type JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Loader2, User, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { listTicketCategories, type TicketCategory } from '@/api/tickets';
import { listDepartments, type Department } from '@/api/departments';
import {
  TicketPriority,
  TicketStatus,
  type TicketPriority as TicketPriorityValue,
  type TicketStatus as TicketStatusValue,
} from '@/types/ticket';

export type SortKey = 'newest' | 'oldest' | 'priority' | 'progress';

export type DashboardFilters = {
  statuses: TicketStatusValue[];
  priorities: TicketPriorityValue[];
  categoryIds: string[];
  departmentIds: string[];
  urgentOnly: boolean;
  mineOnly: boolean;
  overdueOnly: boolean;
  unassignedOnly: boolean;
};

export const EMPTY_FILTERS: DashboardFilters = {
  statuses: [],
  priorities: [],
  categoryIds: [],
  departmentIds: [],
  urgentOnly: false,
  mineOnly: false,
  overdueOnly: false,
  unassignedOnly: false,
};

export const countActiveFilters = (f: DashboardFilters): number =>
  f.statuses.length +
  f.priorities.length +
  f.categoryIds.length +
  f.departmentIds.length +
  (f.urgentOnly ? 1 : 0) +
  (f.mineOnly ? 1 : 0) +
  (f.overdueOnly ? 1 : 0) +
  (f.unassignedOnly ? 1 : 0);

const STATUS_FILTER_OPTIONS: TicketStatusValue[] = [
  TicketStatus.PENDING_APPROVAL,
  TicketStatus.APPROVED,
  TicketStatus.ASSIGNED,
  TicketStatus.IN_PROGRESS,
  TicketStatus.WAITING_INFO,
  TicketStatus.COMPLETED,
  TicketStatus.CLOSED,
  TicketStatus.REJECTED,
  TicketStatus.DRAFT,
];

const PRIORITY_FILTER_OPTIONS: TicketPriorityValue[] = [
  TicketPriority.URGENT,
  TicketPriority.HIGH,
  TicketPriority.NORMAL,
  TicketPriority.LOW,
];

const toggleValue = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter((item) => item !== value) : [...list, value];

type ChipProps = {
  label: string;
  active: boolean;
  onClick: () => void;
};

const Chip = ({ label, active, onClick }: ChipProps): JSX.Element => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={active}
    className={cn(
      'inline-flex h-8 items-center rounded-full border px-3 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
      active
        ? 'border-accent bg-accent text-accent-foreground'
        : 'border-border bg-card text-foreground hover:bg-secondary',
    )}
  >
    {label}
  </button>
);

type ToggleRowProps = {
  label: string;
  icon: JSX.Element;
  active: boolean;
  onClick: () => void;
};

const ToggleRow = ({ label, icon, active, onClick }: ToggleRowProps): JSX.Element => (
  <button
    type="button"
    onClick={onClick}
    role="switch"
    aria-checked={active}
    className={cn(
      'flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
      active
        ? 'border-accent/60 bg-accent/10 text-accent'
        : 'border-border bg-card text-foreground hover:bg-secondary',
    )}
  >
    <span className="flex items-center gap-2">
      {icon}
      {label}
    </span>
    <span
      className={cn(
        'relative inline-flex h-5 w-9 flex-shrink-0 items-center rounded-full transition-colors',
        active ? 'bg-accent' : 'bg-muted',
      )}
      aria-hidden
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-background shadow transition-transform',
          active ? 'translate-x-4' : 'translate-x-0.5',
        )}
      />
    </span>
  </button>
);

type FilterPanelProps = {
  filters: DashboardFilters;
  onFiltersChange: (next: DashboardFilters) => void;
  onReset: () => void;
  onClose: () => void;
  /** Admins see all tickets — show the per-department filter for them. */
  showDepartments?: boolean;
};

const FilterPanel = ({
  filters,
  onFiltersChange,
  onReset,
  onClose,
  showDepartments = false,
}: FilterPanelProps): JSX.Element => {
  const { t } = useTranslation('dashboard');
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [catLoading, setCatLoading] = useState(true);
  const [catError, setCatError] = useState<string | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [deptLoading, setDeptLoading] = useState(showDepartments);
  const [deptQuery, setDeptQuery] = useState('');

  useEffect(() => {
    let active = true;
    setCatLoading(true);
    setCatError(null);
    void listTicketCategories().then((res) => {
      if (!active) return;
      if (res.ok) setCategories(res.data);
      else setCatError(res.error);
      setCatLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!showDepartments) return;
    let active = true;
    setDeptLoading(true);
    void listDepartments({ page_size: 100 }).then((res) => {
      if (!active) return;
      if (res.ok) setDepartments(res.data.items);
      setDeptLoading(false);
    });
    return () => {
      active = false;
    };
  }, [showDepartments]);

  const activeCount = countActiveFilters(filters);

  return (
    <div
      role="dialog"
      aria-label={t('filters.title', { defaultValue: 'Фильтры' })}
      className="absolute right-0 z-40 mt-2 w-[min(20rem,calc(100vw-2rem))] rounded-2xl border border-border bg-card p-4 shadow-xl"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-base text-foreground">
          {t('filters.title', { defaultValue: 'Фильтры' })}
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label={t('filters.close', { defaultValue: 'Закрыть фильтры' })}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
        {/* Status */}
        <fieldset>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('filters.statusLabel', { defaultValue: 'Статус' })}
          </legend>
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTER_OPTIONS.map((status) => (
              <Chip
                key={status}
                label={t(`filters.status.${status}`, { defaultValue: status })}
                active={filters.statuses.includes(status)}
                onClick={() =>
                  onFiltersChange({ ...filters, statuses: toggleValue(filters.statuses, status) })
                }
              />
            ))}
          </div>
        </fieldset>

        {/* Priority */}
        <fieldset>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('filters.priorityLabel', { defaultValue: 'Приоритет' })}
          </legend>
          <div className="flex flex-wrap gap-2">
            {PRIORITY_FILTER_OPTIONS.map((priority) => (
              <Chip
                key={priority}
                label={t(`filters.priority.${priority}`, { defaultValue: priority })}
                active={filters.priorities.includes(priority)}
                onClick={() =>
                  onFiltersChange({
                    ...filters,
                    priorities: toggleValue(filters.priorities, priority),
                  })
                }
              />
            ))}
          </div>
        </fieldset>

        {/* Category */}
        <fieldset>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('filters.categoryLabel', { defaultValue: 'Категория' })}
          </legend>
          {catLoading ? (
            <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
              {t('loading.queue', { defaultValue: 'Загрузка…' })}
            </div>
          ) : catError ? (
            <p className="text-xs text-destructive">
              {t('filters.categoriesError', { defaultValue: 'Не удалось загрузить категории' })}
            </p>
          ) : categories.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              {t('filters.categoriesEmpty', { defaultValue: 'Нет категорий' })}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <Chip
                  key={category.id}
                  label={category.name}
                  active={filters.categoryIds.includes(category.id)}
                  onClick={() =>
                    onFiltersChange({
                      ...filters,
                      categoryIds: toggleValue(filters.categoryIds, category.id),
                    })
                  }
                />
              ))}
            </div>
          )}
        </fieldset>

        {/* Department (admins only — they see all tickets) */}
        {showDepartments && (
          <fieldset>
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {t('filters.departmentLabel', { defaultValue: 'Отдел' })}
            </legend>
            {deptLoading ? (
              <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                {t('loading.queue', { defaultValue: 'Загрузка…' })}
              </div>
            ) : departments.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                {t('filters.departmentsEmpty', { defaultValue: 'Нет отделов' })}
              </p>
            ) : (
              <>
                <input
                  type="text"
                  value={deptQuery}
                  onChange={(e) => setDeptQuery(e.target.value)}
                  placeholder={t('filters.departmentSearch', { defaultValue: 'Поиск отдела…' })}
                  aria-label={t('filters.departmentSearch', { defaultValue: 'Поиск отдела…' })}
                  className="mb-2 h-9 w-full rounded-xl border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground/70 focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15"
                />
                <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto pr-1">
                  {departments
                    .filter((d) =>
                      d.name.toLowerCase().includes(deptQuery.trim().toLowerCase()),
                    )
                    .map((dep) => (
                      <Chip
                        key={dep.id}
                        label={dep.name}
                        active={filters.departmentIds.includes(dep.id)}
                        onClick={() =>
                          onFiltersChange({
                            ...filters,
                            departmentIds: toggleValue(filters.departmentIds, dep.id),
                          })
                        }
                      />
                    ))}
                </div>
              </>
            )}
          </fieldset>
        )}

        {/* Toggles */}
        <div className="space-y-2">
          <ToggleRow
            label={t('filters.urgentOnly', { defaultValue: 'Только срочные' })}
            icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
            active={filters.urgentOnly}
            onClick={() => onFiltersChange({ ...filters, urgentOnly: !filters.urgentOnly })}
          />
          <ToggleRow
            label={t('filters.mineOnly', { defaultValue: 'Мои заявки' })}
            icon={<User className="h-4 w-4" aria-hidden />}
            active={filters.mineOnly}
            onClick={() => onFiltersChange({ ...filters, mineOnly: !filters.mineOnly })}
          />
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3">
        <span className="text-xs text-muted-foreground">
          {t('filters.activeCount', { count: activeCount, defaultValue: 'Активно: {{count}}' })}
        </span>
        <button
          type="button"
          onClick={onReset}
          disabled={activeCount === 0}
          className="inline-flex h-9 items-center rounded-xl border border-border bg-card px-3 text-sm font-medium text-foreground transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('filters.reset', { defaultValue: 'Сбросить' })}
        </button>
      </div>
    </div>
  );
};

export default FilterPanel;
