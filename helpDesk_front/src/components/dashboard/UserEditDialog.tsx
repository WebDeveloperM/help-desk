import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { generatePassword } from '@/lib/password';
import {
  adminCreateUser,
  updateUser,
  type AdminCreateUserInput,
  type AdminUser,
  type UpdateUserInput,
  type UserRole,
} from '@/api/users';
import type { Department } from '@/api/departments';

type UserEditDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'create' | 'edit';
  user?: AdminUser | null;
  departments: Department[];
  onSaved: () => void;
};

const ROLES: readonly UserRole[] = ['user', 'executor', 'department_head', 'admin'];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const UserEditDialog = ({
  open,
  onOpenChange,
  mode,
  user,
  departments,
  onSaved,
}: UserEditDialogProps) => {
  const { t } = useTranslation('dashboard');

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('user');
  const [departmentId, setDepartmentId] = useState('');
  const [position, setPosition] = useState('');
  const [tabelNumber, setTabelNumber] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isEdit = mode === 'edit';

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSubmitting(false);
    if (isEdit && user) {
      setFullName(user.full_name);
      setEmail(user.email);
      setUsername(user.username);
      setPassword('');
      setRole(user.role);
      setDepartmentId(user.department_id ?? '');
      setPosition(user.position ?? '');
      setTabelNumber(user.tabel_number ?? '');
      setIsActive(user.is_active);
      return;
    }
    setFullName('');
    setEmail('');
    setUsername('');
    setPassword('');
    setRole('user');
    setDepartmentId('');
    setPosition('');
    setTabelNumber('');
    setIsActive(true);
  }, [open, isEdit, user]);

  const roleLabel = (value: UserRole): string =>
    t(`users.roles.${value}`, { defaultValue: value });

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setError(t('users.dialog.errors.nameRequired', { defaultValue: 'Укажите имя пользователя' }));
      return;
    }
    if (!EMAIL_RE.test(trimmedEmail)) {
      setError(t('users.dialog.errors.emailInvalid', { defaultValue: 'Укажите корректный email' }));
      return;
    }

    if (!isEdit) {
      if (!username.trim()) {
        setError(t('users.dialog.errors.usernameRequired', { defaultValue: 'Укажите логин' }));
        return;
      }
      if (password.length < 8) {
        setError(
          t('users.dialog.errors.passwordShort', { defaultValue: 'Пароль должен быть не короче 8 символов' })
        );
        return;
      }
    }

    setSubmitting(true);

    if (!isEdit) {
      const input: AdminCreateUserInput = {
        username: username.trim(),
        email: trimmedEmail,
        full_name: trimmedName,
        password,
        role,
        department_id: departmentId || null,
        position: position.trim() || null,
        tabel_number: tabelNumber.trim() || null,
      };
      const res = await adminCreateUser(input);
      setSubmitting(false);
      if (!res.ok) {
        setError(res.error);
        return;
      }
      onSaved();
      onOpenChange(false);
      return;
    }

    if (!user) {
      setSubmitting(false);
      return;
    }

    const payload: UpdateUserInput = {};
    if (trimmedName !== user.full_name) payload.full_name = trimmedName;
    if (trimmedEmail !== user.email) payload.email = trimmedEmail;
    if (role !== user.role) payload.role = role;
    const nextDept = departmentId || null;
    if (nextDept !== (user.department_id ?? null)) payload.department_id = nextDept;
    const nextPos = position.trim() || null;
    const curPos = (user.position ?? '').trim() || null;
    if (nextPos !== curPos) payload.position = nextPos;
    const nextTab = tabelNumber.trim() || null;
    const curTab = (user.tabel_number ?? '').trim() || null;
    if (nextTab !== curTab) payload.tabel_number = nextTab;
    if (isActive !== user.is_active) payload.is_active = isActive;

    if (Object.keys(payload).length === 0) {
      setSubmitting(false);
      onOpenChange(false);
      return;
    }

    const res = await updateUser(user.id, payload);
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    onSaved();
    onOpenChange(false);
  };

  const labelClass = 'block text-sm font-medium text-foreground';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle className="font-display">
            {isEdit
              ? t('users.dialog.editTitle', { defaultValue: 'Изменить пользователя' })
              : t('users.dialog.createTitle', { defaultValue: 'Создать пользователя' })}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? t('users.dialog.editSubtitle', {
                  defaultValue: 'Обновите данные, роль и статус пользователя',
                })
              : t('users.dialog.createSubtitle', {
                  defaultValue: 'Добавьте нового пользователя в систему',
                })}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="ue-full-name" className={labelClass}>
              {t('users.dialog.fields.fullName', { defaultValue: 'Полное имя' })}
            </label>
            <Input
              id="ue-full-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="off"
              autoFocus
              required
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="ue-email" className={labelClass}>
              {t('users.dialog.fields.email', { defaultValue: 'Email' })}
            </label>
            <Input
              id="ue-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="off"
              required
            />
          </div>

          {!isEdit && (
            <div className="space-y-1.5">
              <label htmlFor="ue-username" className={labelClass}>
                {t('users.dialog.fields.username', { defaultValue: 'Логин' })}
              </label>
              <Input
                id="ue-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="off"
                required
              />
            </div>
          )}

          {!isEdit && (
            <div className="space-y-1.5">
              <label htmlFor="ue-password" className={labelClass}>
                {t('users.dialog.fields.password', { defaultValue: 'Пароль' })}
              </label>
              <div className="flex gap-2">
                <Input
                  id="ue-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setPassword(generatePassword())}
                  title={t('users.dialog.fields.generate', { defaultValue: 'Сгенерировать пароль' })}
                  aria-label={t('users.dialog.fields.generate', { defaultValue: 'Сгенерировать пароль' })}
                  className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border bg-card transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden />
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                {t('users.dialog.fields.passwordHint', { defaultValue: 'Минимум 8 символов' })}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="ue-role" className={labelClass}>
                {t('users.dialog.fields.role', { defaultValue: 'Роль' })}
              </label>
              <Select
                id="ue-role"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {roleLabel(r)}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="ue-department" className={labelClass}>
                {t('users.dialog.fields.department', { defaultValue: 'Отдел' })}
              </label>
              <Select
                id="ue-department"
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
              >
                <option value="">
                  {t('users.dialog.fields.noDepartment', { defaultValue: '— без отдела —' })}
                </option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="ue-position" className={labelClass}>
                {t('users.dialog.fields.position', { defaultValue: 'Должность' })}
                <span className="ml-1 font-normal text-muted-foreground">
                  {t('users.dialog.fields.optional', { defaultValue: '(необязательно)' })}
                </span>
              </label>
              <Input
                id="ue-position"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                autoComplete="off"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="ue-tabel" className={labelClass}>
                {t('users.dialog.fields.tabel', { defaultValue: 'Табельный №' })}
                <span className="ml-1 font-normal text-muted-foreground">
                  {t('users.dialog.fields.optional', { defaultValue: '(необязательно)' })}
                </span>
              </label>
              <Input
                id="ue-tabel"
                value={tabelNumber}
                onChange={(e) => setTabelNumber(e.target.value)}
                autoComplete="off"
              />
            </div>
          </div>

          {isEdit && (
            <div className="flex items-center justify-between rounded-xl border border-border bg-background px-3.5 py-3">
              <div>
                <div className="text-sm font-medium text-foreground">
                  {t('users.dialog.fields.active', { defaultValue: 'Активен' })}
                </div>
                <div className="text-xs text-muted-foreground">
                  {t('users.dialog.fields.activeHint', {
                    defaultValue: 'Отключённый пользователь не может входить в систему',
                  })}
                </div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={isActive}
                onClick={() => setIsActive((v) => !v)}
                aria-label={t('users.dialog.fields.active', { defaultValue: 'Активен' })}
                className={cn(
                  'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
                  isActive ? 'bg-accent' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'inline-block h-5 w-5 transform rounded-full bg-card shadow transition-transform',
                    isActive ? 'translate-x-5' : 'translate-x-0.5'
                  )}
                />
              </button>
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-xl bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </div>
          )}

          <DialogFooter className="px-0 pt-2">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex h-11 items-center justify-center rounded-xl border border-border bg-card px-4 text-sm font-semibold transition-colors hover:bg-secondary focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {t('users.dialog.cancel', { defaultValue: 'Отмена' })}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex h-11 items-center justify-center rounded-xl bg-accent px-4 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50 focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {submitting
                ? '…'
                : isEdit
                  ? t('users.dialog.save', { defaultValue: 'Сохранить' })
                  : t('users.dialog.create', { defaultValue: 'Создать' })}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default UserEditDialog;
