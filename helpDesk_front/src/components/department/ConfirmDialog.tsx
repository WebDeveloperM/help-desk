import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  body: string;
  confirmLabel: string;
  destructive?: boolean;
  onConfirm: () => Promise<{ ok: boolean; error?: string }>;
};

const ConfirmDialog = ({
  open,
  onOpenChange,
  title,
  body,
  confirmLabel,
  destructive = false,
  onConfirm,
}: ConfirmDialogProps) => {
  const { t } = useTranslation('departments');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    setError(null);
    setSubmitting(true);
    const result = await onConfirm();
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error ?? '');
      return;
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{body}</DialogDescription>
        </DialogHeader>
        {error && (
          <div role="alert" className="text-sm text-destructive bg-destructive/10 rounded-xl px-3 py-2 mb-2">
            {error}
          </div>
        )}
        <DialogFooter className="px-0">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="inline-flex items-center justify-center px-4 h-10 rounded-xl border border-border bg-card text-sm font-semibold hover:bg-secondary transition-colors focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20"
          >
            {t('actions.cancel')}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={submitting}
            className={`inline-flex items-center justify-center px-4 h-10 rounded-xl text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-4 disabled:opacity-50 ${
              destructive
                ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90 focus-visible:ring-destructive/20'
                : 'bg-accent text-accent-foreground hover:bg-accent/90 focus-visible:ring-accent/20'
            }`}
          >
            {submitting ? '…' : confirmLabel}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConfirmDialog;
