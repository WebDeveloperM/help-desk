import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  createDepartment,
  updateDepartment,
  type Department,
  type DepartmentInput,
} from '@/api/departments';

type DepartmentDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  department?: Department | null;
  onSaved: (saved: Department) => void;
};

const DepartmentDialog = ({ open, onOpenChange, department, onSaved }: DepartmentDialogProps) => {
  const { t } = useTranslation('departments');
  const isEdit = Boolean(department);

  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [nameUz, setNameUz] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCode(department?.code ?? '');
    setName(department?.name ?? '');
    setNameUz(department?.name_uz ?? '');
    setIsActive(department?.is_active ?? true);
    setError(null);
    setSubmitting(false);
  }, [open, department]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!code.trim()) {
      setError(t('dialog.errors.codeRequired'));
      return;
    }
    if (!name.trim()) {
      setError(t('dialog.errors.nameRequired'));
      return;
    }

    setSubmitting(true);
    const payload: DepartmentInput = {
      code: code.trim(),
      name: name.trim(),
      name_uz: nameUz.trim() || null,
      is_active: isActive,
    };

    const result = isEdit && department
      ? await updateDepartment(department.id, payload)
      : await createDepartment(payload);

    setSubmitting(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }
    onSaved(result.data);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>{isEdit ? t('dialog.editTitle') : t('dialog.createTitle')}</DialogTitle>
          {isEdit && department && (
            <DialogDescription>
              {t('dialog.numberHint', { number: department.number })}
            </DialogDescription>
          )}
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="dept-code" className="block text-sm font-medium text-foreground mb-1">
                {t('dialog.fields.code')}
              </label>
              <Input
                id="dept-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="IT-01"
                autoFocus
              />
              <p className="text-xs text-muted-foreground mt-1">{t('dialog.fields.codeHint')}</p>
            </div>
            <div>
              <label htmlFor="dept-name" className="block text-sm font-medium text-foreground mb-1">
                {t('dialog.fields.name')}
              </label>
              <Input id="dept-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label htmlFor="dept-name-uz" className="block text-sm font-medium text-foreground mb-1">
                {t('dialog.fields.nameUz')}
              </label>
              <Input id="dept-name-uz" value={nameUz} onChange={(e) => setNameUz(e.target.value)} />
            </div>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 rounded-md border-border accent-accent"
              />
              {t('dialog.fields.isActive')}
            </label>
            {error && (
              <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2">
                {error}
              </div>
            )}
          </div>
          <DialogFooter className="px-0 mt-6">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex items-center justify-center px-4 h-10 rounded-xl border border-border bg-card text-sm font-semibold hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {t('actions.cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center justify-center px-4 h-10 rounded-xl bg-accent text-accent-foreground text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
            >
              {submitting ? '…' : t('actions.save')}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default DepartmentDialog;
