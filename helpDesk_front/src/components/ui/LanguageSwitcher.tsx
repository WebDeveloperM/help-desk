import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Globe } from 'lucide-react';

import { cn } from '@/lib/utils';
import {
  LANGUAGE_LABELS,
  LANGUAGE_SHORT_LABELS,
  SUPPORTED_LANGUAGES,
  isSupportedLanguage,
  type SupportedLanguage,
} from '@/i18n';

type LanguageSwitcherVariant = 'icon' | 'compact' | 'full';

interface LanguageSwitcherProps {
  className?: string;
  variant?: LanguageSwitcherVariant;
  align?: 'left' | 'right';
  tone?: 'light' | 'dark';
  direction?: 'down' | 'up';
}

const LanguageSwitcher = ({
  className,
  variant = 'compact',
  align = 'right',
  tone = 'light',
  direction = 'down',
}: LanguageSwitcherProps): ReactNode => {
  const { t, i18n } = useTranslation('common');
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const current: SupportedLanguage = isSupportedLanguage(i18n.resolvedLanguage)
    ? i18n.resolvedLanguage
    : isSupportedLanguage(i18n.language?.split('-')[0])
      ? (i18n.language.split('-')[0] as SupportedLanguage)
      : 'ru';

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleSelect = async (lng: SupportedLanguage) => {
    setOpen(false);
    if (lng === current) return;
    await i18n.changeLanguage(lng);
  };

  const triggerBase =
    'inline-flex items-center gap-2 rounded-xl border transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20';
  const triggerTone =
    tone === 'dark'
      ? 'border-white/10 bg-white/5 text-slate-200 hover:bg-white/10'
      : 'border-border bg-card text-foreground hover:bg-secondary';

  const sizeClasses =
    variant === 'icon'
      ? 'h-10 w-10 justify-center'
      : 'px-3.5 h-10 text-sm font-medium';

  const triggerLabel =
    variant === 'icon'
      ? LANGUAGE_SHORT_LABELS[current]
      : variant === 'full'
        ? LANGUAGE_LABELS[current]
        : LANGUAGE_SHORT_LABELS[current];

  const menuToneClasses =
    tone === 'dark'
      ? 'border-white/10 bg-card text-slate-200'
      : 'border-border bg-card text-foreground';

  const itemHoverClasses =
    tone === 'dark' ? 'hover:bg-white/5' : 'hover:bg-muted';

  return (
    <div ref={containerRef} className={cn('relative inline-flex', className)}>
      <button
        type="button"
        className={cn(triggerBase, triggerTone, sizeClasses)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t('language.switchAria')}
        onClick={() => setOpen((prev) => !prev)}
      >
        <Globe className="h-3.5 w-3.5" aria-hidden />
        {variant !== 'icon' && <span>{triggerLabel}</span>}
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={t('language.label')}
          className={cn(
            'absolute z-50 min-w-[160px] overflow-hidden rounded-xl border shadow-lg',
            align === 'right' ? 'right-0' : 'left-0',
            direction === 'up' ? 'bottom-full mb-1' : 'top-full mt-1',
            menuToneClasses,
          )}
        >
          {SUPPORTED_LANGUAGES.map((lng) => {
            const selected = lng === current;
            return (
              <li key={lng}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => void handleSelect(lng)}
                  className={cn(
                    'flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left text-sm',
                    itemHoverClasses,
                    selected && (tone === 'dark' ? 'bg-white/5' : 'bg-muted'),
                  )}
                >
                  <span className="flex items-center gap-2">
                    <span
                      className={cn(
                        'text-[11px] font-medium',
                        tone === 'dark' ? 'text-slate-500' : 'text-muted-foreground',
                      )}
                    >
                      {LANGUAGE_SHORT_LABELS[lng]}
                    </span>
                    <span>{LANGUAGE_LABELS[lng]}</span>
                  </span>
                  {selected && <Check className="h-3.5 w-3.5" aria-hidden />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default LanguageSwitcher;
