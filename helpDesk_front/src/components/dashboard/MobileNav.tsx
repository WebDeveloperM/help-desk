import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';
import {
  BarChart3,
  Building2,
  LayoutDashboard,
  Settings,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MobileNavProps {
  activeNav?: string;
  onNavChange?: (nav: string) => void;
}

interface NavItem {
  labelKey: string;
  shortKey: string;
  href: string;
  icon: LucideIcon;
  navKey: string;
}

const NAV_ITEMS: NavItem[] = [
  { labelKey: 'nav.dashboard', shortKey: 'nav.short.dashboard', href: '/dashboard', icon: LayoutDashboard, navKey: 'Dashboard' },
  { labelKey: 'nav.departments', shortKey: 'nav.short.departments', href: '/departments', icon: Building2, navKey: 'Departments' },
  { labelKey: 'nav.reports', shortKey: 'nav.short.reports', href: '/reports', icon: BarChart3, navKey: 'Reports' },
  { labelKey: 'nav.settings', shortKey: 'nav.short.settings', href: '/settings', icon: Settings, navKey: 'Settings' },
];

const isMatch = (pathname: string, href: string): boolean => {
  if (pathname === href) return true;
  if (href === '/dashboard' && pathname === '/') return true;
  return pathname.startsWith(`${href}/`);
};

const MobileNav = ({ activeNav, onNavChange }: MobileNavProps): JSX.Element => {
  const location = useLocation();
  const { t } = useTranslation('dashboard');

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card md:hidden"
      aria-label={t('mobileNav.aria')}
    >
      <div className="flex h-16 items-stretch">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = isMatch(location.pathname, item.href) || activeNav === item.navKey;
          const label = t(item.labelKey);

          return (
            <Link
              key={item.navKey}
              to={item.href}
              onClick={() => onNavChange?.(item.navKey)}
              aria-current={active ? 'page' : undefined}
              aria-label={label}
              className={cn(
                'group relative flex flex-1 flex-col items-center justify-center gap-1.5 transition-colors',
                active ? 'text-accent' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <span
                className={cn(
                  'absolute left-1/2 top-0 h-[2px] w-8 -translate-x-1/2 rounded-full transition-colors',
                  active ? 'bg-accent' : 'bg-transparent',
                )}
                aria-hidden
              />
              <Icon className="h-[18px] w-[18px]" aria-hidden />
              <span className="text-[11px] font-medium">
                {t(item.shortKey)}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
};

export default MobileNav;
