import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Check, Copy, RefreshCw, Search, UserPlus } from 'lucide-react';
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
import {
  adminCreateUser,
  listUsers,
  updateUserDepartment,
  type AdminCreateUserInput,
  type AdminUser,
} from '@/api/users';
import { generatePassword } from '@/lib/password';
import type { Department } from '@/api/departments';

type AddEmployeeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  department: Department;
  onChanged: () => void;
};

const ROLES: AdminCreateUserInput['role'][] = ['user', 'department_head', 'executor'];

const usernameFromEmail = (email: string): string => {
  const at = email.indexOf('@');
  return at > 0 ? email.slice(0, at) : '';
};

const looksLikeEmail = (value: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

type Mode = 'search' | 'create';

const AddEmployeeDialog = ({ open, onOpenChange, department, onChanged }: AddEmployeeDialogProps) => {
  const { t } = useTranslation('departments');

  const [mode, setMode] = useState<Mode>('search');

  // search state
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [assigningId, setAssigningId] = useState<string | null>(null);

  // create state
  const [username, setUsername] = useState('');
  const [usernameAutoFill, setUsernameAutoFill] = useState(true);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [fullNameUz, setFullNameUz] = useState('');
  const [position, setPosition] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<AdminCreateUserInput['role']>('user');
  const [createError, setCreateError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    setMode('search');
    setQuery('');
    setSearchError(null);
    setAssigningId(null);
    setUsers([]);
    resetCreateForm('');
    const controller = new AbortController();
    setSearchLoading(true);
    listUsers({ page_size: 100, signal: controller.signal }).then((res) => {
      setSearchLoading(false);
      if (!res.ok) {
        setSearchError(res.error);
        return;
      }
      setUsers(res.data.items);
    });
    return () => controller.abort();
  }, [open]);

  const resetCreateForm = (prefilledEmail: string) => {
    setUsername(usernameFromEmail(prefilledEmail));
    setUsernameAutoFill(true);
    setEmail(prefilledEmail);
    setFullName('');
    setFullNameUz('');
    setPosition('');
    setPhone('');
    setPassword(generatePassword());
    setRole('user');
    setCreateError(null);
    setSubmitting(false);
    setCreatedPassword(null);
    setCopied(false);
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return users
      .filter((u) => u.is_active && u.department_id !== department.id)
      .filter((u) =>
        !q ||
        u.full_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q)
      );
  }, [users, query, department.id]);

  const handleAssign = async (user: AdminUser) => {
    setSearchError(null);
    setAssigningId(user.id);
    const result = await updateUserDepartment(user.id, department.id);
    setAssigningId(null);
    if (!result.ok) {
      setSearchError(result.error);
      return;
    }
    onChanged();
    onOpenChange(false);
  };

  const handleSwitchToCreate = () => {
    resetCreateForm(looksLikeEmail(query) ? query.trim() : '');
    setMode('create');
  };

  const handleEmailChange = (next: string) => {
    setEmail(next);
    if (usernameAutoFill) setUsername(usernameFromEmail(next));
  };

  const handleUsernameChange = (next: string) => {
    setUsername(next);
    setUsernameAutoFill(false);
  };

  const handleCreateSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);
    setSubmitting(true);
    const result = await adminCreateUser({
      username: username.trim(),
      email: email.trim(),
      full_name: fullName.trim(),
      full_name_uz: fullNameUz.trim() || null,
      password,
      role,
      department_id: department.id,
      position: position.trim() || null,
      phone: phone.trim() || null,
    });
    setSubmitting(false);
    if (!result.ok) {
      setCreateError(result.error);
      return;
    }
    setCreatedPassword(password);
    onChanged();
  };

  const handleCopy = async () => {
    if (!createdPassword) return;
    await navigator.clipboard.writeText(createdPassword);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const renderSearch = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('addEmployee.title')}</DialogTitle>
        <DialogDescription>
          {t('addEmployee.subtitle', { number: department.number })}
        </DialogDescription>
      </DialogHeader>

      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('addEmployee.search')}
          className="pl-10"
          aria-label={t('addEmployee.search')}
          autoFocus
        />
      </div>

      {searchError && (
        <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mb-2">
          {searchError}
        </div>
      )}

      <div className="max-h-72 overflow-y-auto border border-border rounded-xl">
        {searchLoading ? (
          <div className="px-4 py-6 text-sm text-muted-foreground text-center">…</div>
        ) : filtered.length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground text-center">
            {t('addEmployee.empty')}
          </div>
        ) : (
          <ul>
            {filtered.map((u) => (
              <li
                key={u.id}
                className="flex items-center gap-3 px-4 py-2 border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">{u.full_name || u.email}</div>
                  <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                </div>
                <button
                  type="button"
                  onClick={() => handleAssign(u)}
                  disabled={assigningId !== null}
                  className="inline-flex items-center gap-1.5 px-3 h-9 bg-accent text-accent-foreground rounded-xl text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  {assigningId === u.id ? '…' : t('addEmployee.assign')}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <DialogFooter className="px-0 mt-4">
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="inline-flex items-center justify-center px-4 h-10 rounded-xl border border-border bg-card text-sm font-semibold hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
        >
          {t('actions.close')}
        </button>
        <button
          type="button"
          onClick={handleSwitchToCreate}
          className="inline-flex items-center justify-center px-4 h-10 rounded-xl bg-accent text-accent-foreground text-sm font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
        >
          {t('addEmployee.createNew')}
        </button>
      </DialogFooter>
    </>
  );

  const renderCreate = () => (
    <>
      <DialogHeader>
        <div className="flex items-center gap-2">
          {!createdPassword && (
            <button
              type="button"
              onClick={() => setMode('search')}
              aria-label={t('addEmployee.backToSearch')}
              title={t('addEmployee.backToSearch')}
              className="inline-flex items-center justify-center h-9 w-9 rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}
          <DialogTitle>
            {createdPassword ? t('createUser.successTitle') : t('createUser.title')}
          </DialogTitle>
        </div>
        <DialogDescription>
          {createdPassword
            ? t('createUser.successBody')
            : t('createUser.subtitle', { number: department.number })}
        </DialogDescription>
      </DialogHeader>

      {createdPassword ? (
        <div className="space-y-4">
          <div className="flex items-center gap-2 bg-muted rounded-xl px-3.5 py-3">
            <code className="flex-1 font-mono text-sm break-all">{createdPassword}</code>
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 h-10 bg-accent text-accent-foreground rounded-xl text-sm font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? t('createUser.copied') : t('createUser.copy')}
            </button>
          </div>
          <DialogFooter className="px-0">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex items-center justify-center px-4 h-10 bg-accent text-accent-foreground rounded-xl text-sm font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {t('actions.close')}
            </button>
          </DialogFooter>
        </div>
      ) : (
        <form onSubmit={handleCreateSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="ae-email" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.email')}
              </label>
              <Input
                id="ae-email"
                type="email"
                value={email}
                onChange={(e) => handleEmailChange(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="ae-username" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.username')}
              </label>
              <Input
                id="ae-username"
                value={username}
                onChange={(e) => handleUsernameChange(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground mt-1">{t('createUser.fields.usernameHint')}</p>
            </div>
            <div className="md:col-span-2">
              <label htmlFor="ae-name" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.fullName')}
              </label>
              <Input
                id="ae-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="ae-name-uz" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.fullNameUz')}
              </label>
              <Input
                id="ae-name-uz"
                value={fullNameUz}
                onChange={(e) => setFullNameUz(e.target.value)}
              />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="ae-password" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.password')}
              </label>
              <div className="flex gap-2">
                <Input
                  id="ae-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setPassword(generatePassword())}
                  title={t('createUser.fields.generate')}
                  aria-label={t('createUser.fields.generate')}
                  className="inline-flex items-center justify-center h-11 w-11 shrink-0 border border-border bg-card rounded-xl hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{t('createUser.fields.passwordHint')}</p>
            </div>
            <div>
              <label htmlFor="ae-role" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.role')}
              </label>
              <Select
                id="ae-role"
                value={role}
                onChange={(e) => setRole(e.target.value as AdminCreateUserInput['role'])}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {t(`createUser.roles.${r}`)}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label htmlFor="ae-position" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.position')}
              </label>
              <Input id="ae-position" value={position} onChange={(e) => setPosition(e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <label htmlFor="ae-phone" className="block text-sm font-medium text-foreground mb-1">
                {t('createUser.fields.phone')}
              </label>
              <Input id="ae-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>
          {createError && (
            <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mt-4">
              {createError}
            </div>
          )}
          <DialogFooter className="px-0 mt-6">
            <button
              type="button"
              onClick={() => setMode('search')}
              className="inline-flex items-center justify-center px-4 h-10 rounded-xl border border-border bg-card text-sm font-semibold hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {t('addEmployee.backToSearch')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center justify-center px-4 h-10 rounded-xl bg-accent text-accent-foreground text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {submitting ? '…' : t('createUser.submit')}
            </button>
          </DialogFooter>
        </form>
      )}
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        {mode === 'search' ? renderSearch() : renderCreate()}
      </DialogContent>
    </Dialog>
  );
};

export default AddEmployeeDialog;
