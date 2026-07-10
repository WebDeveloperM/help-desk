import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, UserPlus, UserCheck, Mail, UserMinus, KeyRound } from 'lucide-react';
import {
  listUsersByDepartment,
  type Department,
  type DepartmentUser,
} from '@/api/departments';
import { updateUserDepartment } from '@/api/users';
import AddEmployeeDialog from './AddEmployeeDialog';
import ConfirmDialog from './ConfirmDialog';
import ResetPasswordDialog from './ResetPasswordDialog';

type DepartmentDetailDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  department: Department | null;
  canManage: boolean;
};

const DepartmentDetailDrawer = ({
  open,
  onOpenChange,
  department,
  canManage,
}: DepartmentDetailDrawerProps) => {
  const { t } = useTranslation('departments');

  const [users, setUsers] = useState<DepartmentUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<DepartmentUser | null>(null);
  const [resetTarget, setResetTarget] = useState<DepartmentUser | null>(null);

  const reloadUsers = useCallback(
    async (signal?: AbortSignal) => {
      if (!department) return;
      setLoading(true);
      setError(null);
      const res = await listUsersByDepartment(department.id, { signal });
      if (signal?.aborted) return;
      setLoading(false);
      if (!res.ok) {
        setError(res.error);
        return;
      }
      setUsers(res.data);
    },
    [department]
  );

  useEffect(() => {
    if (!open || !department) return;
    const controller = new AbortController();
    void reloadUsers(controller.signal);
    return () => controller.abort();
  }, [open, department, reloadUsers]);

  const handleRemoveConfirm = async (): Promise<{ ok: boolean; error?: string }> => {
    if (!removeTarget) return { ok: false };
    setError(null);
    const res = await updateUserDepartment(removeTarget.id, null);
    if (!res.ok) {
      return { ok: false, error: res.error };
    }
    setRemoveTarget(null);
    await reloadUsers();
    return { ok: true };
  };

  if (!department) return null;

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={t('drawer.title', { number: department.number })}
        className={`fixed right-0 top-0 z-50 h-screen w-full max-w-md bg-card border-l border-border rounded-l-2xl shadow-lg transition-transform duration-200 ease-out flex flex-col ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <header className="flex items-start justify-between gap-3 p-6 border-b border-border">
          <div className="min-w-0">
            <div className="text-xs font-mono text-muted-foreground">#{department.number}</div>
            <h2 className="font-display text-xl font-semibold text-foreground truncate">{department.name}</h2>
            <div className="text-sm text-muted-foreground mt-0.5">{department.code}</div>
          </div>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label={t('actions.close')}
            className="inline-flex items-center justify-center h-10 w-10 rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-muted-foreground" />
              {t('drawer.tabUsers')} ({users.length})
            </h3>
            {canManage && (
              <button
                type="button"
                onClick={() => setAddOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 h-10 bg-accent text-accent-foreground rounded-xl text-sm font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
              >
                <UserPlus className="h-3.5 w-3.5" />
                {t('drawer.addEmployee')}
              </button>
            )}
          </div>

          {error && (
            <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mb-3">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-sm text-muted-foreground text-center py-6">…</div>
          ) : users.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-6">
              {t('drawer.noUsers')}
            </div>
          ) : (
            <ul className="space-y-2">
              {users.map((u) => (
                <li
                  key={u.id}
                  className="flex items-start gap-3 p-3.5 border border-border rounded-xl"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {u.full_name || u.email}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mt-0.5">
                      <Mail className="h-3 w-3" aria-hidden />
                      <span className="truncate">{u.email}</span>
                    </div>
                  </div>
                  {canManage && (
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setResetTarget(u)}
                        aria-label={t('drawer.resetPasswordAria', { name: u.full_name || u.email })}
                        title={t('drawer.resetPassword')}
                        className="inline-flex items-center justify-center h-9 w-9 rounded-xl text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                      >
                        <KeyRound className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setRemoveTarget(u)}
                        aria-label={t('drawer.removeAria', { name: u.full_name || u.email })}
                        title={t('drawer.removeFromDepartment')}
                        className="inline-flex items-center justify-center h-9 w-9 rounded-xl text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-destructive/20"
                      >
                        <UserMinus className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {canManage && (
        <>
          <AddEmployeeDialog
            open={addOpen}
            onOpenChange={(o) => {
              setAddOpen(o);
              if (!o) void reloadUsers();
            }}
            department={department}
            onChanged={() => void reloadUsers()}
          />
          {removeTarget && (
            <ConfirmDialog
              open={Boolean(removeTarget)}
              onOpenChange={(o) => {
                if (!o) setRemoveTarget(null);
              }}
              destructive
              title={t('removeUser.title')}
              body={t('removeUser.body', {
                name: removeTarget.full_name || removeTarget.email,
                department: department.name,
              })}
              confirmLabel={t('removeUser.confirm')}
              onConfirm={handleRemoveConfirm}
            />
          )}
          <ResetPasswordDialog
            open={Boolean(resetTarget)}
            onOpenChange={(o) => {
              if (!o) setResetTarget(null);
            }}
            user={resetTarget}
          />
        </>
      )}
    </>
  );
};

export default DepartmentDetailDrawer;
