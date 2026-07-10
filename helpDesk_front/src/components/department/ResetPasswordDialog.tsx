import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Copy, RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { resetUserPassword } from '@/api/users';
import { generatePassword } from '@/lib/password';
import type { DepartmentUser } from '@/api/departments';

type ResetPasswordDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: DepartmentUser | null;
};

const ResetPasswordDialog = ({ open, onOpenChange, user }: ResetPasswordDialogProps) => {
  const { t } = useTranslation('departments');

  const [password, setPassword] = useState('');
  const [issued, setIssued] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    setPassword(generatePassword());
    setIssued(null);
    setError(null);
    setSubmitting(false);
    setCopied(false);
  }, [open]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user) return;
    setError(null);
    setSubmitting(true);
    const res = await resetUserPassword(user.id, password);
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error);
      return;
    }
    setIssued(res.data.password);
  };

  const handleCopy = async () => {
    if (!issued) return;
    await navigator.clipboard.writeText(issued);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  if (!user) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>
            {issued ? t('resetPassword.successTitle') : t('resetPassword.title')}
          </DialogTitle>
          <DialogDescription>
            {issued
              ? t('resetPassword.successBody')
              : t('resetPassword.subtitle', { name: user.full_name || user.email })}
          </DialogDescription>
        </DialogHeader>

        {issued ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 bg-muted rounded-xl px-3.5 py-3">
              <code className="flex-1 font-mono text-sm break-all">{issued}</code>
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
          <form onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label htmlFor="rp-password" className="block text-sm font-medium text-foreground">
                {t('resetPassword.fields.password')}
              </label>
              <div className="flex gap-2">
                <Input
                  id="rp-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
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
              <p className="text-xs text-muted-foreground">
                {t('createUser.fields.passwordHint')}
              </p>
            </div>
            {error && (
              <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mt-4">
                {error}
              </div>
            )}
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
                {submitting ? '…' : t('resetPassword.submit')}
              </button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ResetPasswordDialog;
