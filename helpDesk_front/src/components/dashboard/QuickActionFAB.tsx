import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickActionFABProps {
  onClick?: () => void;
  className?: string;
  ariaLabel?: string;
}

const QuickActionFAB = ({
  onClick,
  className,
  ariaLabel,
}: QuickActionFABProps): JSX.Element => {
  const { t } = useTranslation('dashboard');
  const label = ariaLabel ?? t('actions.newRequest');
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cn(
        'group fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-accent-foreground shadow-lg transition-all duration-200',
        'hover:bg-accent/90 active:scale-95',
        'focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
        'md:hidden',
        className,
      )}
    >
      <span
        className="absolute inset-0 -z-10 animate-ping rounded-full bg-accent/30"
        aria-hidden
      />
      <Plus
        className="h-6 w-6 transition-transform duration-200 group-hover:rotate-90"
        aria-hidden
      />
    </button>
  );
};

export default QuickActionFAB;
