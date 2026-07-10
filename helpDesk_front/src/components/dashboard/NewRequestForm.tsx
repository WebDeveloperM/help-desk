import { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { AlertCircle, Loader2 } from 'lucide-react';
import { createTicket, listTicketCategories, type TicketCategory } from '@/api/tickets';
import { listDepartments, listUsersByDepartment, type Department } from '@/api/departments';
import { getCurrentUser } from '@/api/users';

type Priority = 'low' | 'normal' | 'high' | 'urgent';

type NewRequestFormData = {
  title: string;
  description: string;
  priority: Priority;
  department: string;
  category: string;
  executor_user_ids: string[];
  desired_completion_date?: string;
  is_urgent: boolean;
};

const buildSchema = (t: (key: string) => string) =>
  z.object({
    title: z.string().min(3, t('form.validation.titleMin')).max(200, t('form.validation.titleMax')),
    description: z.string().min(10, t('form.validation.descMin')).max(2000, t('form.validation.descMax')),
    priority: z.enum(['low', 'normal', 'high', 'urgent'], { message: t('form.validation.priorityRequired') }),
    department: z.string().min(1, t('form.validation.departmentRequired')),
    category: z.string().min(1, t('form.validation.categoryRequired')),
    executor_user_ids: z.array(z.string()).min(1, t('form.validation.executorsRequired')),
    desired_completion_date: z.string().optional(),
    is_urgent: z.boolean().default(false),
  });

interface NewRequestFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

const PRIORITY_VALUES: Priority[] = ['low', 'normal', 'high', 'urgent'];

const NewRequestForm = ({ open, onOpenChange, onSuccess }: NewRequestFormProps) => {
  const { token } = useAuth();
  const { t } = useTranslation('tickets');
  const { t: tCommon } = useTranslation('common');
  const schema = useMemo(() => buildSchema(t), [t]);
  const priorityOptions = useMemo(
    () => PRIORITY_VALUES.map((value) => ({ value, label: t(`priority.${value}`) })),
    [t],
  );
  const [formData, setFormData] = useState<Partial<NewRequestFormData>>({
    priority: 'normal',
    is_urgent: false,
    executor_user_ids: [],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [categories, setCategories] = useState<TicketCategory[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentUsers, setDepartmentUsers] = useState<{ id: string; full_name: string; email: string }[]>([]);
  const [currentUserDepartmentId, setCurrentUserDepartmentId] = useState<string | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [departmentUsersLoading, setDepartmentUsersLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const closeTimerRef = useRef<number | null>(null);

  const effectiveDepartmentId = formData.department ?? currentUserDepartmentId ?? null;

  const cancelCloseTimer = useCallback(() => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  useEffect(() => cancelCloseTimer, [cancelCloseTimer]);

  const loadOptions = useCallback(async () => {
    if (!token) return;
    setOptionsLoading(true);
    setSubmitError(null);
    try {
      const [userResult, catResult, deptResult] = await Promise.all([
        getCurrentUser(),
        listTicketCategories(),
        listDepartments({ page: 1, page_size: 100, is_active: true }),
      ]);
      if (userResult.ok) {
        const rawId = userResult.data.department_id;
        const departmentId = rawId != null ? String(rawId) : null;
        setCurrentUserDepartmentId(departmentId);
        if (departmentId) {
          setFormData((prev) => ({ ...prev, department: departmentId }));
        }
      } else {
        setCurrentUserDepartmentId(null);
      }
      if (catResult.ok) setCategories(catResult.data);
      else setCategories([]);
      if (deptResult.ok) setDepartments(deptResult.data.items);
      else setDepartments([]);
    } finally {
      setOptionsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (open && token) void loadOptions();
  }, [open, token, loadOptions]);

  useEffect(() => {
    const loadDepartmentUsers = async () => {
      const deptId = effectiveDepartmentId;
      if (!token || !deptId) {
        setDepartmentUsers([]);
        setDepartmentUsersLoading(false);
        return;
      }
      setDepartmentUsersLoading(true);
      const result = await listUsersByDepartment(deptId);
      if (result.ok) setDepartmentUsers(result.data);
      else setDepartmentUsers([]);
      setDepartmentUsersLoading(false);
    };
    void loadDepartmentUsers();
  }, [token, effectiveDepartmentId]);

  const handleChange = <K extends keyof NewRequestFormData>(field: K, value: NewRequestFormData[K]) => {
    setFormData((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'department') {
        next.executor_user_ids = [];
      }
      return next;
    });
    setSubmitError(null);
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    cancelCloseTimer();
    setSubmitError(null);
    setIsSubmitting(true);
    setErrors({});

    try {
      const validatedData = schema.parse(formData);
      if (!token) {
        setSubmitError(t('form.errors.noToken'));
        setIsSubmitting(false);
        return;
      }
      if (!currentUserDepartmentId) {
        setSubmitError(t('form.errors.noDepartment'));
        setIsSubmitting(false);
        return;
      }
      const assignedDeptId = effectiveDepartmentId ?? currentUserDepartmentId;
      const result = await createTicket({
        title: validatedData.title,
        description: validatedData.description,
        category_id: validatedData.category,
        creator_department_id: currentUserDepartmentId,
        assigned_department_id: assignedDeptId,
        priority: validatedData.priority,
        desired_completion_date: validatedData.desired_completion_date
          ? new Date(validatedData.desired_completion_date).toISOString()
          : null,
        executor_user_ids: validatedData.executor_user_ids,
      });

      if (result.ok) {
        setFormData({ priority: 'normal', is_urgent: false, executor_user_ids: [] });
        setSubmitError(null);
        setSuccessMessage(t('form.success.created'));
        onSuccess?.();
        closeTimerRef.current = window.setTimeout(() => {
          closeTimerRef.current = null;
          setSuccessMessage(null);
          onOpenChange(false);
        }, 1500);
      } else {
        setSubmitError(result.error);
      }
    } catch (err) {
      if (err instanceof z.ZodError) {
        const fieldErrors: Record<string, string> = {};
        err.issues.forEach((issue) => {
          const path = issue.path[0];
          if (path != null) fieldErrors[String(path)] = issue.message;
        });
        setErrors(fieldErrors);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecutorToggle = (userId: string) => {
    setFormData((prev) => {
      const current = prev.executor_user_ids ?? [];
      const next = current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId];
      return { ...prev, executor_user_ids: next };
    });
    setSubmitError(null);
  };

  const handleClose = () => {
    if (!isSubmitting) {
      cancelCloseTimer();
      setFormData({ priority: 'normal', is_urgent: false, executor_user_ids: [] });
      setErrors({});
      setSubmitError(null);
      setSuccessMessage(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent onClose={handleClose} aria-describedby="new-request-description">
        <DialogHeader>
          <DialogTitle id="new-request-title">{t('form.title')}</DialogTitle>
          <DialogDescription id="new-request-description">
            {t('form.subtitle')}
          </DialogDescription>
        </DialogHeader>

        {successMessage ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-lg font-medium text-foreground">{successMessage}</p>
            <p className="mt-2 text-sm text-muted-foreground">{t('form.success.refresh')}</p>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="space-y-4" aria-label={t('form.formAria')}>
          {submitError && (
            <div role="alert" className="flex items-center gap-2 rounded-xl border border-destructive/50 bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />
              <span>{submitError}</span>
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium text-foreground">
              {t('form.labels.title')} <span className="text-destructive">*</span>
            </label>
            <Input
              id="title"
              value={formData.title ?? ''}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder={t('form.placeholders.title')}
              className={cn(errors.title && 'border-destructive')}
            />
            {errors.title && (
              <div className="flex items-center gap-1 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                <span>{errors.title}</span>
              </div>
            )}
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label htmlFor="description" className="text-sm font-medium text-foreground">
              {t('form.labels.description')} <span className="text-destructive">*</span>
            </label>
            <textarea
              id="description"
              value={formData.description ?? ''}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder={t('form.placeholders.description')}
              rows={4}
              className={cn(
                'flex w-full rounded-xl border border-input bg-background px-3.5 py-2.5 text-[15px] text-foreground',
                'placeholder:text-muted-foreground',
                'focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15',
                'disabled:cursor-not-allowed disabled:opacity-50 resize-none',
                errors.description && 'border-destructive'
              )}
            />
            {errors.description && (
              <div className="flex items-center gap-1 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                <span>{errors.description}</span>
              </div>
            )}
          </div>

          {/* Priority and Department Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="priority" className="text-sm font-medium text-foreground">
                {t('form.labels.priority')} <span className="text-destructive">*</span>
              </label>
              <Select
                id="priority"
                value={formData.priority ?? ''}
                onChange={(e) => handleChange('priority', e.target.value as NewRequestFormData['priority'])}
                className={cn(errors.priority && 'border-destructive')}
              >
                <option value="">{t('form.placeholders.priority')}</option>
                {priorityOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
              {errors.priority && (
                <div className="flex items-center gap-1 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <span>{errors.priority}</span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="department" className="text-sm font-medium text-foreground">
                {t('form.labels.department')} <span className="text-destructive">*</span>
              </label>
              <Select
                id="department"
                value={effectiveDepartmentId ?? ''}
                onChange={(e) => handleChange('department', e.target.value)}
                className={cn(errors.department && 'border-destructive')}
                disabled={optionsLoading}
              >
                <option value="">{t('form.placeholders.department')}</option>
                {currentUserDepartmentId &&
                  !departments.some((d) => d.id === currentUserDepartmentId) && (
                    <option value={currentUserDepartmentId}>{t('form.yourDepartment')}</option>
                  )}
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.id === currentUserDepartmentId
                      ? t('form.yourDepartmentNamed', { name: d.name })
                      : d.name}
                  </option>
                ))}
              </Select>
              <span className="text-xs text-muted-foreground">
                {effectiveDepartmentId
                  ? t('form.help.executorOnly')
                  : t('form.help.selectDepartment')}
              </span>
              {errors.department && (
                <div className="flex items-center gap-1 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <span>{errors.department}</span>
                </div>
              )}
            </div>
          </div>

          {/* Category */}
          <div className="space-y-2">
            <label htmlFor="category" className="text-sm font-medium text-foreground">
              {t('form.labels.category')} <span className="text-destructive">*</span>
            </label>
            <Select
              id="category"
              value={formData.category ?? ''}
              onChange={(e) => handleChange('category', e.target.value)}
              className={cn(errors.category && 'border-destructive')}
              disabled={optionsLoading}
              aria-describedby="category-hint"
            >
              <option value="">{t('form.placeholders.category')}</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </Select>
            <span id="category-hint" className="text-xs text-muted-foreground">
              {optionsLoading
                ? t('form.help.categoryLoading')
                : categories.length === 0
                  ? t('form.help.noCategories')
                  : t('form.help.selectCategory')}
            </span>
            {errors.category && (
              <div className="flex items-center gap-1 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                <span>{errors.category}</span>
              </div>
            )}
          </div>

          {/* Executors */}
          {effectiveDepartmentId && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                {t('form.labels.executors')}
              </label>
              {departmentUsersLoading ? (
                <div className="flex items-center gap-2 rounded-xl border border-border bg-muted/30 px-3.5 py-4 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin shrink-0" aria-hidden />
                  {t('form.executors.loading')}
                </div>
              ) : departmentUsers.length > 0 ? (
                <>
                  <div className="rounded-xl border border-border bg-background p-3 max-h-40 overflow-y-auto space-y-2">
                    {departmentUsers.map((u) => (
                      <label
                        key={u.id}
                        className="flex items-center gap-2 cursor-pointer hover:bg-muted/50 rounded-lg px-2 py-1.5 -mx-2 -my-1.5"
                      >
                        <input
                          type="checkbox"
                          checked={(formData.executor_user_ids ?? []).includes(u.id)}
                          onChange={() => handleExecutorToggle(u.id)}
                          className="w-4 h-4 rounded-md border-border bg-background text-accent focus:ring-2 focus:ring-accent focus:ring-offset-2 cursor-pointer"
                          aria-label={t('form.executors.assignAria', { name: u.full_name })}
                        />
                        <span className="text-sm text-foreground">{u.full_name}</span>
                        {u.email && (
                          <span className="text-xs text-muted-foreground">({u.email})</span>
                        )}
                      </label>
                    ))}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {t('form.help.executorsHelp')}
                  </span>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t('form.executors.noUsers')}
                </p>
              )}
              {errors.executor_user_ids && (
                <div className="flex items-center gap-1 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <span>{errors.executor_user_ids}</span>
                </div>
              )}
            </div>
          )}

          {/* Desired Completion Date */}
          <div className="space-y-2">
            <label htmlFor="desired_completion_date" className="text-sm font-medium text-foreground">
              {t('form.labels.desiredCompletion')}
            </label>
            <Input
              id="desired_completion_date"
              type="date"
              value={formData.desired_completion_date ?? ''}
              onChange={(e) => handleChange('desired_completion_date', e.target.value)}
              min={new Date().toISOString().split('T')[0]}
            />
          </div>

          {/* Urgent Checkbox (UI only; backend does not support on create) */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_urgent"
              checked={formData.is_urgent ?? false}
              onChange={(e) => handleChange('is_urgent', e.target.checked)}
              className="w-4 h-4 rounded-md border-border bg-background text-accent focus:ring-2 focus:ring-accent focus:ring-offset-2 cursor-pointer"
            />
            <label htmlFor="is_urgent" className="text-sm font-medium text-foreground cursor-pointer">
              {t('form.labels.markUrgent')}
            </label>
          </div>

          <DialogFooter>
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-semibold text-foreground transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:opacity-50"
            >
              {tCommon('actions.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || optionsLoading}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-accent-foreground transition-colors hover:bg-accent/90 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {t('form.actions.create')}
            </button>
          </DialogFooter>
        </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default NewRequestForm;
