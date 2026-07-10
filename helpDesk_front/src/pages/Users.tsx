import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from '@/components/ui/sidebar';
import { ThemeProvider } from '../contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import Sidebar from '../components/dashboard/Sidebar';
import { Select } from '@/components/ui/select';
import {
  AlertTriangle,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  RotateCw,
  Search,
  ShieldAlert,
  Trash2,
  UsersRound,
} from 'lucide-react';
import {
  deleteUser,
  getUserActivity,
  listUsers,
  type AdminUser,
  type UserActivity,
  type UserActivityMap,
  type UserRole,
} from '@/api/users';
import { listDepartments, type Department } from '@/api/departments';
import UserEditDialog from '@/components/dashboard/UserEditDialog';
import ResetPasswordDialog from '@/components/department/ResetPasswordDialog';
import ConfirmDialog from '@/components/department/ConfirmDialog';

type LoadState = 'loading' | 'error' | 'ready';
type RoleFilter = 'all' | UserRole;

const ROLE_OPTIONS: readonly RoleFilter[] = ['all', 'user', 'executor', 'department_head', 'admin'];

const ROLE_PILL: Record<UserRole, string> = {
  admin: 'bg-destructive/12 text-destructive',
  department_head: 'bg-accent/12 text-accent',
  executor: 'bg-accent/8 text-accent',
  user: 'bg-muted text-muted-foreground',
};

const EMPTY_ACTIVITY: UserActivity = { created: 0, active: 0, completed: 0 };

const UsersContent = () => {
  const { open } = useSidebar();
  const { t } = useTranslation('dashboard');
  const { profile } = useAuth();
  const [activeNav] = useState('Users');
  const [isDesktop, setIsDesktop] = useState(false);

  const isAdmin = useMemo(
    () => (profile?.roles ?? []).map((r) => r.toLowerCase()).includes('admin'),
    [profile]
  );

  const [state, setState] = useState<LoadState>('loading');
  const [error, setError] = useState('');
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [activity, setActivity] = useState<UserActivityMap>({});
  const [departments, setDepartments] = useState<Department[]>([]);

  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [activeOnly, setActiveOnly] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editMode, setEditMode] = useState<'create' | 'edit'>('create');
  const [editUser, setEditUser] = useState<AdminUser | null>(null);

  const [resetUser, setResetUser] = useState<AdminUser | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);

  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 768);
    checkDesktop();
    window.addEventListener('resize', checkDesktop);
    return () => window.removeEventListener('resize', checkDesktop);
  }, []);

  const fetchAll = useCallback(async (signal?: AbortSignal, silent = false) => {
    if (!silent) setState('loading');
    setError('');
    const [usersRes, activityRes, deptRes] = await Promise.all([
      listUsers({ page_size: 200, signal }),
      getUserActivity({ signal }),
      listDepartments({ page_size: 100, signal }),
    ]);
    if (signal?.aborted) return;
    if (!usersRes.ok) {
      setError(usersRes.error);
      setState('error');
      return;
    }
    setUsers(usersRes.data.items);
    setActivity(activityRes.ok ? activityRes.data : {});
    setDepartments(deptRes.ok ? deptRes.data.items : []);
    setState('ready');
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    const controller = new AbortController();
    void fetchAll(controller.signal);
    return () => controller.abort();
  }, [isAdmin, fetchAll]);

  const reload = useCallback(() => {
    void fetchAll(undefined, true);
  }, [fetchAll]);

  const deptNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of departments) map.set(d.id, d.name);
    return map;
  }, [departments]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (roleFilter !== 'all' && u.role !== roleFilter) return false;
      if (deptFilter !== 'all' && (u.department_id ?? '') !== deptFilter) return false;
      if (activeOnly && !u.is_active) return false;
      if (!q) return true;
      return (
        u.full_name.toLowerCase().includes(q) ||
        u.username.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q)
      );
    });
  }, [users, search, roleFilter, deptFilter, activeOnly]);

  const roleLabel = useCallback(
    (role: UserRole): string => t(`users.roles.${role}`, { defaultValue: role }),
    [t]
  );

  const roleFilterLabel = useCallback(
    (value: RoleFilter): string =>
      value === 'all'
        ? t('users.filters.allRoles', { defaultValue: 'Все роли' })
        : roleLabel(value),
    [t, roleLabel]
  );

  const openCreate = () => {
    setEditMode('create');
    setEditUser(null);
    setEditOpen(true);
  };

  const openEdit = (user: AdminUser) => {
    setEditMode('edit');
    setEditUser(user);
    setEditOpen(true);
  };

  const openReset = (user: AdminUser) => {
    setResetUser(user);
    setResetOpen(true);
  };

  const departmentName = (id: string | null | undefined): string =>
    (id && deptNameById.get(id)) || '—';

  const activityFor = (id: string): UserActivity => activity[id] ?? EMPTY_ACTIVITY;

  const mainStyle = {
    width: isDesktop ? `calc(100vw - ${open ? '300px' : '80px'})` : '100%',
    marginLeft: isDesktop ? (open ? '300px' : '80px') : '0',
  };

  return (
    <div className="flex min-h-screen w-full bg-background font-sans">
      <div className="hidden md:block">
        <ShadcnSidebar>
          <Sidebar activeNav={activeNav} onNavChange={() => {}} />
        </ShadcnSidebar>
      </div>

      <main
        className="min-h-screen overflow-auto p-4 pt-14 pb-20 transition-all duration-300 md:p-6 md:pt-6 md:pb-6"
        style={mainStyle}
        aria-label={t('users.page.aria', { defaultValue: 'Управление пользователями' })}
      >
        <div className="mx-auto max-w-7xl">
          {!isAdmin ? (
            <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
              <div className="rounded-full bg-destructive/10 p-3 text-destructive" aria-hidden>
                <ShieldAlert className="h-6 w-6" />
              </div>
              <h1 className="font-display text-xl font-semibold text-foreground">
                {t('users.noAccess.title', { defaultValue: 'Нет доступа' })}
              </h1>
              <p className="max-w-md text-sm text-muted-foreground">
                {t('users.noAccess.description', {
                  defaultValue: 'Этот раздел доступен только администраторам.',
                })}
              </p>
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <h1 className="font-display text-3xl font-semibold text-foreground" id="users-heading">
                      {t('users.page.title', { defaultValue: 'Пользователи' })}
                    </h1>
                    {state === 'ready' && (
                      <span className="inline-flex items-center rounded-full bg-muted px-3 py-1 text-sm font-medium tabular-nums text-muted-foreground">
                        {users.length}
                      </span>
                    )}
                  </div>
                  <p className="mt-2 text-[15px] text-muted-foreground" id="users-description">
                    {t('users.page.description', {
                      defaultValue: 'Все пользователи, их роли, отделы и активность по задачам',
                    })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={openCreate}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-accent px-4 font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                  aria-label={t('users.actions.create', { defaultValue: 'Создать пользователя' })}
                >
                  <Plus className="h-4 w-4" aria-hidden />
                  <span>{t('users.actions.create', { defaultValue: 'Создать пользователя' })}</span>
                </button>
              </div>

              {/* Toolbar */}
              <div className="mb-6 rounded-2xl border border-border bg-card p-4">
                <div className="flex flex-col gap-4">
                  <div className="relative">
                    <Search
                      className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                      aria-hidden
                    />
                    <input
                      type="search"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder={t('users.filters.searchPlaceholder', {
                        defaultValue: 'Поиск по имени, логину или email',
                      })}
                      className="h-11 w-full rounded-xl border border-input bg-background pl-10 pr-4 text-[15px] text-foreground transition-colors focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15"
                      aria-label={t('users.filters.searchAria', { defaultValue: 'Поиск пользователей' })}
                    />
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_auto]">
                    <Select
                      value={roleFilter}
                      onChange={(e) => setRoleFilter(e.target.value as RoleFilter)}
                      aria-label={t('users.filters.roleAria', { defaultValue: 'Фильтр по роли' })}
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>
                          {roleFilterLabel(r)}
                        </option>
                      ))}
                    </Select>
                    <Select
                      value={deptFilter}
                      onChange={(e) => setDeptFilter(e.target.value)}
                      aria-label={t('users.filters.departmentAria', { defaultValue: 'Фильтр по отделу' })}
                    >
                      <option value="all">
                        {t('users.filters.allDepartments', { defaultValue: 'Все отделы' })}
                      </option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={activeOnly}
                      onClick={() => setActiveOnly((v) => !v)}
                      className={cn(
                        'inline-flex h-11 items-center justify-center rounded-xl border px-4 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
                        activeOnly
                          ? 'border-accent bg-accent/10 text-accent'
                          : 'border-border bg-card text-muted-foreground hover:bg-secondary'
                      )}
                    >
                      {t('users.filters.activeOnly', { defaultValue: 'Только активные' })}
                    </button>
                  </div>
                </div>
              </div>

              {/* States */}
              {state === 'loading' && (
                <div
                  className="flex flex-col items-center justify-center py-24 text-muted-foreground"
                  role="status"
                  aria-live="polite"
                >
                  <Loader2 className="h-8 w-8 animate-spin text-accent" aria-hidden />
                  <p className="mt-3 text-sm">
                    {t('users.state.loading', { defaultValue: 'Загрузка пользователей…' })}
                  </p>
                </div>
              )}

              {state === 'error' && (
                <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
                  <div className="rounded-full bg-destructive/10 p-3 text-destructive" aria-hidden>
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">
                      {t('users.state.errorTitle', { defaultValue: 'Не удалось загрузить пользователей' })}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{error}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void fetchAll()}
                    className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                  >
                    <RotateCw className="h-4 w-4" aria-hidden />
                    {t('users.state.retry', { defaultValue: 'Повторить' })}
                  </button>
                </div>
              )}

              {state === 'ready' && filtered.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-border bg-card py-16 text-center">
                  <div className="rounded-full bg-muted p-3 text-muted-foreground" aria-hidden>
                    <UsersRound className="h-6 w-6" />
                  </div>
                  <p className="font-medium text-foreground">
                    {users.length === 0
                      ? t('users.state.emptyTitle', { defaultValue: 'Пока нет пользователей' })
                      : t('users.state.noMatchesTitle', { defaultValue: 'Ничего не найдено' })}
                  </p>
                  <p className="max-w-md text-sm text-muted-foreground">
                    {users.length === 0
                      ? t('users.state.emptyDescription', {
                          defaultValue: 'Создайте первого пользователя, чтобы начать работу.',
                        })
                      : t('users.state.noMatchesDescription', {
                          defaultValue: 'Измените поиск или фильтры.',
                        })}
                  </p>
                </div>
              )}

              {state === 'ready' && filtered.length > 0 && (
                <>
                  {/* Desktop table */}
                  <div className="hidden overflow-hidden rounded-2xl border border-border bg-card md:block">
                    <div className="overflow-x-auto">
                      <table
                        className="w-full min-w-[880px]"
                        aria-label={t('users.table.aria', { defaultValue: 'Таблица пользователей' })}
                      >
                        <thead className="sticky top-0 z-10 bg-card">
                          <tr className="border-b border-border">
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium tabular-nums text-muted-foreground">
                              №
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.user', { defaultValue: 'Пользователь' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.tabel', { defaultValue: 'Табельный №' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.email', { defaultValue: 'Email' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.role', { defaultValue: 'Роль' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.department', { defaultValue: 'Отдел' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.tasks', { defaultValue: 'Задачи' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                              {t('users.table.status', { defaultValue: 'Статус' })}
                            </th>
                            <th scope="col" className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                              {t('users.table.actions', { defaultValue: 'Действия' })}
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {filtered.map((u, index) => {
                            const act = activityFor(u.id);
                            return (
                              <tr
                                key={u.id}
                                className="border-b border-border last:border-0 transition-colors hover:bg-muted/50"
                              >
                                <td className="px-4 py-3 text-sm tabular-nums text-muted-foreground">
                                  {index + 1}
                                </td>
                                <td className="px-4 py-3">
                                  <div className="font-medium text-foreground">{u.full_name || '—'}</div>
                                  <div className="text-sm tabular-nums text-muted-foreground">@{u.username}</div>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="text-sm tabular-nums text-foreground">
                                    {u.tabel_number || '—'}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="text-sm text-muted-foreground">{u.email || '—'}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <span
                                    className={cn(
                                      'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
                                      ROLE_PILL[u.role]
                                    )}
                                  >
                                    {roleLabel(u.role)}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <span className="text-sm text-foreground">
                                    {departmentName(u.department_id)}
                                  </span>
                                </td>
                                <td className="px-4 py-3">
                                  <TaskStats act={act} t={t} />
                                </td>
                                <td className="px-4 py-3">
                                  <StatusPill active={u.is_active} t={t} />
                                </td>
                                <td className="px-4 py-3">
                                  <div className="flex items-center justify-end gap-1.5">
                                    <RowActions
                                      user={u}
                                      onEdit={openEdit}
                                      onReset={openReset}
                                      onDelete={setDeleteTarget}
                                      t={t}
                                    />
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Mobile cards */}
                  <div className="flex flex-col gap-3 md:hidden">
                    {filtered.map((u) => {
                      const act = activityFor(u.id);
                      return (
                        <div key={u.id} className="rounded-2xl border border-border bg-card p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate font-medium text-foreground">{u.full_name || '—'}</div>
                              <div className="truncate text-sm tabular-nums text-muted-foreground">
                                @{u.username}
                              </div>
                              <div className="mt-0.5 truncate text-sm text-muted-foreground">{u.email || '—'}</div>
                            </div>
                            <StatusPill active={u.is_active} t={t} />
                          </div>

                          <div className="mt-3 flex flex-wrap items-center gap-2">
                            <span
                              className={cn(
                                'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
                                ROLE_PILL[u.role]
                              )}
                            >
                              {roleLabel(u.role)}
                            </span>
                            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                              {departmentName(u.department_id)}
                            </span>
                            {u.tabel_number && (
                              <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-1 text-xs font-medium tabular-nums text-muted-foreground">
                                {t('users.table.tabel', { defaultValue: 'Табельный №' })}: {u.tabel_number}
                              </span>
                            )}
                          </div>

                          <div className="mt-3">
                            <TaskStats act={act} t={t} />
                          </div>

                          <div className="mt-3 flex items-center gap-1.5 border-t border-border pt-3">
                            <RowActions
                              user={u}
                              onEdit={openEdit}
                              onReset={openReset}
                              onDelete={setDeleteTarget}
                              t={t}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </main>

      <UserEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode={editMode}
        user={editUser}
        departments={departments}
        onSaved={reload}
      />

      <ResetPasswordDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        user={
          resetUser
            ? { id: resetUser.id, full_name: resetUser.full_name, email: resetUser.email }
            : null
        }
      />

      {deleteTarget && (
        <ConfirmDialog
          open={Boolean(deleteTarget)}
          onOpenChange={(o) => {
            if (!o) setDeleteTarget(null);
          }}
          destructive
          title={t('users.delete.title', { defaultValue: 'Удалить пользователя' })}
          body={t('users.delete.body', {
            defaultValue: 'Пользователь «{{name}}» будет отключён. Продолжить?',
            name: deleteTarget.full_name || deleteTarget.username,
          })}
          confirmLabel={t('users.delete.confirm', { defaultValue: 'Удалить' })}
          onConfirm={async () => {
            const res = await deleteUser(deleteTarget.id);
            if (res.ok) {
              reload();
              return { ok: true };
            }
            return { ok: false, error: res.error };
          }}
        />
      )}
    </div>
  );
};

type TFn = ReturnType<typeof useTranslation>['t'];

const TaskStats = ({ act, t }: { act: UserActivity; t: TFn }) => (
  <div className="flex items-center gap-1.5 text-xs tabular-nums">
    <span
      className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-foreground"
      title={t('users.tasks.activeFull', { defaultValue: 'Активных задач' })}
    >
      <span className="text-muted-foreground">{t('users.tasks.activeShort', { defaultValue: 'А' })}</span>
      {act.active}
    </span>
    <span
      className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-accent"
      title={t('users.tasks.completedFull', { defaultValue: 'Завершённых задач' })}
    >
      <span className="opacity-70">{t('users.tasks.completedShort', { defaultValue: 'З' })}</span>
      {act.completed}
    </span>
    <span
      className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-muted-foreground"
      title={t('users.tasks.createdFull', { defaultValue: 'Созданных задач' })}
    >
      <span className="opacity-70">{t('users.tasks.createdShort', { defaultValue: 'С' })}</span>
      {act.created}
    </span>
  </div>
);

const StatusPill = ({ active, t }: { active: boolean; t: TFn }) => (
  <span
    className={cn(
      'inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-xs font-medium',
      active ? 'bg-accent/12 text-accent' : 'bg-muted text-muted-foreground'
    )}
  >
    {active
      ? t('users.status.active', { defaultValue: 'Активен' })
      : t('users.status.inactive', { defaultValue: 'Отключён' })}
  </span>
);

type RowActionsProps = {
  user: AdminUser;
  onEdit: (user: AdminUser) => void;
  onReset: (user: AdminUser) => void;
  onDelete: (user: AdminUser) => void;
  t: TFn;
};

const RowActions = ({ user, onEdit, onReset, onDelete, t }: RowActionsProps) => {
  const name = user.full_name || user.username;
  return (
    <>
      <button
        type="button"
        onClick={() => onEdit(user)}
        className="inline-flex h-10 w-10 items-center justify-center rounded-xl transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
        aria-label={t('users.actions.editAria', { defaultValue: 'Изменить {{name}}', name })}
      >
        <Pencil className="h-4 w-4 text-muted-foreground" aria-hidden />
      </button>
      <button
        type="button"
        onClick={() => onReset(user)}
        className="inline-flex h-10 w-10 items-center justify-center rounded-xl transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
        aria-label={t('users.actions.resetPasswordAria', { defaultValue: 'Сбросить пароль {{name}}', name })}
      >
        <KeyRound className="h-4 w-4 text-muted-foreground" aria-hidden />
      </button>
      <button
        type="button"
        onClick={() => onDelete(user)}
        className="inline-flex h-10 w-10 items-center justify-center rounded-xl transition-colors hover:bg-destructive/10 focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
        aria-label={t('users.actions.deleteAria', { defaultValue: 'Удалить {{name}}', name })}
      >
        <Trash2 className="h-4 w-4 text-destructive" aria-hidden />
      </button>
    </>
  );
};

const Users = () => {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <UsersContent />
      </SidebarProvider>
    </ThemeProvider>
  );
};

export default Users;
