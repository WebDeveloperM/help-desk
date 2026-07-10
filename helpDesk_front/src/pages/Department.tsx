import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SidebarProvider, Sidebar as ShadcnSidebar, useSidebar } from '@/components/ui/sidebar';
import { ThemeProvider } from '../contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import Sidebar from '../components/dashboard/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Building2, Users, UserCheck, Plus, Search, Edit, Trash2 } from 'lucide-react';
import {
  deleteDepartment,
  listDepartments,
  type Department as DepartmentType,
} from '@/api/departments';
import DepartmentDialog from '@/components/department/DepartmentDialog';
import DepartmentDetailDrawer from '@/components/department/DepartmentDetailDrawer';
import ConfirmDialog from '@/components/department/ConfirmDialog';

const DepartmentContent = () => {
  const { open } = useSidebar();
  const { t } = useTranslation('departments');
  const { profile } = useAuth();
  const [activeNav] = useState('Departments');
  const [searchQuery, setSearchQuery] = useState('');
  const [departments, setDepartments] = useState<DepartmentType[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<DepartmentType | null>(null);
  const [drawerDept, setDrawerDept] = useState<DepartmentType | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DepartmentType | null>(null);

  const isAdmin = useMemo(
    () => (profile?.roles ?? []).map((r) => r.toLowerCase()).includes('admin'),
    [profile]
  );

  const reload = async () => {
    setLoading(true);
    setLoadError(null);
    const res = await listDepartments({ page_size: 100 });
    setLoading(false);
    if (!res.ok) {
      setLoadError(res.error);
      return;
    }
    setDepartments(res.data.items);
  };

  useEffect(() => {
    void reload();
  }, []);

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return departments;
    return departments.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.code.toLowerCase().includes(q) ||
        String(d.number).includes(q)
    );
  }, [departments, searchQuery]);

  const stats = useMemo(() => {
    const total = departments.length;
    const active = departments.filter((d) => d.is_active).length;
    return [
      { title: t('stats.total'), value: String(total), icon: Building2 },
      { title: t('stats.active'), value: String(active), icon: UserCheck },
      { title: t('stats.employees'), value: '—', icon: Users },
    ];
  }, [departments, t]);

  const handleSaved = (saved: DepartmentType) => {
    setDepartments((prev) => {
      const idx = prev.findIndex((d) => d.id === saved.id);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = saved;
        return copy;
      }
      return [...prev, saved].sort((a, b) => a.number - b.number);
    });
  };

  const handleDelete = async (): Promise<{ ok: boolean; error?: string }> => {
    if (!deleteTarget) return { ok: false };
    const res = await deleteDepartment(deleteTarget.id);
    if (!res.ok) return { ok: false, error: res.error };
    setDepartments((prev) => prev.filter((d) => d.id !== deleteTarget.id));
    setDeleteTarget(null);
    return { ok: true };
  };

  const openDrawer = (dept: DepartmentType) => {
    setDrawerDept(dept);
    setDrawerOpen(true);
  };

  return (
    <div className="flex min-h-screen bg-background font-sans w-full">
      <div className="hidden md:block">
        <ShadcnSidebar>
          <Sidebar activeNav={activeNav} onNavChange={() => {}} />
        </ShadcnSidebar>
      </div>

      <main
        className={cn(
          'p-4 md:p-6 overflow-auto transition-all duration-300 pt-14 md:pt-6 min-h-screen pb-20 md:pb-6 w-full',
          open ? 'md:w-[calc(100vw-300px)] md:ml-[300px]' : 'md:w-[calc(100vw-80px)] md:ml-[80px]'
        )}
        aria-label={t('page.aria')}
      >
        <div className="max-w-7xl mx-auto">
          <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl font-semibold text-foreground mb-2" id="departments-heading">
                {t('page.title')}
              </h1>
              <p className="text-[15px] text-muted-foreground" id="departments-description">
                {t('page.description')}
              </p>
            </div>
            {isAdmin && (
              <button
                type="button"
                onClick={() => {
                  setEditing(null);
                  setDialogOpen(true);
                }}
                className="inline-flex items-center justify-center gap-2 px-4 h-11 bg-accent text-accent-foreground rounded-xl font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                aria-label={t('actions.create')}
              >
                <Plus className="h-4 w-4" aria-hidden />
                <span>{t('actions.create')}</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" role="region" aria-label={t('stats.title')}>
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.title}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {stat.title}
                    </CardTitle>
                    <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
                  </CardHeader>
                  <CardContent>
                    <div className="font-display text-3xl font-semibold text-foreground">{stat.value}</div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search
                    className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
                    aria-hidden
                  />
                  <input
                    type="search"
                    placeholder={t('actions.search')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full h-11 pl-10 pr-4 rounded-xl border border-input bg-background text-[15px] text-foreground focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15"
                    aria-label={t('actions.searchAria')}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('list.title')}</CardTitle>
              <CardDescription>{t('list.description')}</CardDescription>
            </CardHeader>
            <CardContent>
              {loadError && (
                <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mb-3">
                  {loadError}
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full" role="table" aria-label={t('list.tableAria')}>
                  <thead>
                    <tr className="border-b border-border">
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-muted-foreground w-16">
                        {t('list.columns.number')}
                      </th>
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                        {t('list.columns.name')}
                      </th>
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                        {t('list.columns.code')}
                      </th>
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                        {t('list.columns.status')}
                      </th>
                      <th scope="col" className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                        {t('list.columns.actions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={5} className="py-6 px-4 text-center text-sm text-muted-foreground">
                          {t('list.loading')}
                        </td>
                      </tr>
                    ) : filtered.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-6 px-4 text-center text-sm text-muted-foreground">
                          {t('list.empty')}
                        </td>
                      </tr>
                    ) : (
                      filtered.map((dept) => (
                        <tr
                          key={dept.id}
                          className="border-b border-border hover:bg-muted/50 transition-colors cursor-pointer"
                          onClick={() => openDrawer(dept)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              openDrawer(dept);
                            }
                          }}
                          tabIndex={0}
                          role="button"
                          aria-label={t('actions.openAria', { name: dept.name })}
                        >
                          <td className="py-3 px-4">
                            <span className="font-mono text-sm text-muted-foreground">#{dept.number}</span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-medium text-foreground">{dept.name}</div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-muted-foreground">{dept.code}</span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={cn(
                                'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
                                dept.is_active
                                  ? 'bg-accent/12 text-accent'
                                  : 'bg-muted text-muted-foreground'
                              )}
                            >
                              {dept.is_active ? t('list.status.active') : t('list.status.inactive')}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                              {isAdmin && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setEditing(dept);
                                      setDialogOpen(true);
                                    }}
                                    className="inline-flex items-center justify-center h-10 w-10 rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                                    aria-label={t('actions.editAria', { name: dept.name })}
                                  >
                                    <Edit className="h-4 w-4 text-muted-foreground" aria-hidden />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setDeleteTarget(dept)}
                                    className="inline-flex items-center justify-center h-10 w-10 rounded-xl hover:bg-destructive/10 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
                                    aria-label={t('actions.deleteAria', { name: dept.name })}
                                  >
                                    <Trash2 className="h-4 w-4 text-destructive" aria-hidden />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      <DepartmentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        department={editing}
        onSaved={handleSaved}
      />

      <DepartmentDetailDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        department={drawerDept}
        canManage={isAdmin}
      />

      {deleteTarget && (
        <ConfirmDialog
          open={Boolean(deleteTarget)}
          onOpenChange={(o) => {
            if (!o) setDeleteTarget(null);
          }}
          destructive
          title={t('delete.title')}
          body={t('delete.body', { name: deleteTarget.name, number: deleteTarget.number })}
          confirmLabel={t('delete.confirm')}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
};

const Department = () => {
  return (
    <ThemeProvider>
      <SidebarProvider>
        <DepartmentContent />
      </SidebarProvider>
    </ThemeProvider>
  );
};

export default Department;
