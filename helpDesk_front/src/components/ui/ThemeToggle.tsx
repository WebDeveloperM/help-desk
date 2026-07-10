import { useTheme } from '../../contexts/ThemeContext';
import { Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  className?: string;
  variant?: 'icon' | 'button';
}

const ThemeToggle = ({ className, variant = 'icon' }: ThemeToggleProps) => {
  const { theme, toggleTheme } = useTheme();

  if (variant === 'button') {
    return (
      <button
        onClick={toggleTheme}
        className={cn(
          'inline-flex items-center gap-2 px-4 h-10 rounded-xl text-sm font-medium transition-colors',
          'bg-card hover:bg-secondary text-text-primary border border-border',
          'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
          className
        )}
        aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      >
        {theme === 'light' ? (
          <>
            <Moon className="w-4 h-4" />
            <span className="hidden sm:inline">Dark Mode</span>
          </>
        ) : (
          <>
            <Sun className="w-4 h-4" />
            <span className="hidden sm:inline">Light Mode</span>
          </>
        )}
      </button>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'inline-flex items-center justify-center h-10 w-10 rounded-xl transition-colors',
        'text-text-secondary hover:text-text-primary',
        'hover:bg-surfaceHover focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20',
        className
      )}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <Moon className="w-5 h-5" />
      ) : (
        <Sun className="w-5 h-5" />
      )}
    </button>
  );
};

export default ThemeToggle;
