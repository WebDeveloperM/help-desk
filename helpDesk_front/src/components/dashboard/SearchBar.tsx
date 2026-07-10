import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  className?: string;
}

const SearchBar = ({
  placeholder,
  value,
  onChange,
  className,
}: SearchBarProps): JSX.Element => {
  const { t } = useTranslation('common');
  const effectivePlaceholder = placeholder ?? `${t('actions.search')}...`;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange?.(e.target.value);
  };

  return (
    <div
      role="search"
      className={cn(
        'flex h-11 flex-1 items-center gap-3 rounded-xl border border-input bg-background px-3.5 transition-colors focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/15',
        className,
      )}
    >
      <Search
        className="h-4 w-4 flex-shrink-0 text-muted-foreground"
        aria-hidden
      />
      <input
        type="search"
        placeholder={effectivePlaceholder}
        value={value}
        onChange={handleChange}
        className="min-w-0 flex-1 border-none bg-transparent text-[15px] text-foreground outline-none placeholder:text-muted-foreground"
        aria-label={effectivePlaceholder}
        autoComplete="off"
      />
    </div>
  );
};

export default SearchBar;
