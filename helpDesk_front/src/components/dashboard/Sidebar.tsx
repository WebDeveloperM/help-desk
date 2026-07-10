import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  SidebarBody,
  SidebarHeader,
  SidebarLink,
  useSidebar,
} from '@/components/ui/sidebar';
import { motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Settings,
  Building2,
  Headset,
  Users2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import ThemeToggle from '@/components/ui/ThemeToggle';
import LanguageSwitcher from '@/components/ui/LanguageSwitcher';
import NotificationBell from '@/components/dashboard/NotificationBell';

interface SidebarProps {
  activeNav?: string;
  onNavChange?: (nav: string) => void;
}

const NODE_SERIAL = 'OPS-NODE-7A';

const Sidebar = ({ activeNav: _activeNav, onNavChange }: SidebarProps): ReactNode => {
  const { open, animate } = useSidebar();
  const location = useLocation();
  const { t } = useTranslation(['common', 'dashboard']);
  const { profile } = useAuth();
  const expanded = animate ? open : true;

  const isAdmin = (profile?.roles ?? []).map((r) => r.toLowerCase()).includes('admin');

  const navItems = [
    {
      label: t('dashboard:nav.dashboard'),
      icon: <LayoutDashboard className="h-5 w-5" />,
      href: '/dashboard',
    },
    {
      label: t('dashboard:nav.departments'),
      icon: <Building2 className="h-5 w-5" />,
      href: '/departments',
    },
    ...(isAdmin
      ? [
          {
            label: t('dashboard:nav.users', { defaultValue: 'Пользователи' }),
            icon: <Users2 className="h-5 w-5" />,
            href: '/users',
          },
        ]
      : []),
    {
      label: t('dashboard:nav.reports'),
      icon: <BarChart3 className="h-5 w-5" />,
      href: '/reports',
    },
    {
      label: t('dashboard:nav.settings'),
      icon: <Settings className="h-5 w-5" />,
      href: '/settings',
    },
  ];

  return (
    <SidebarBody className="flex h-full flex-col overflow-hidden border-r border-border bg-card">
      <SidebarHeader className="flex-shrink-0">
        <div
          className={cn(
            'flex gap-3',
            expanded ? 'flex-row items-center' : 'flex-col items-center',
          )}
        >
          <div
            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-border bg-accent/10"
            aria-hidden
          >
            <Headset className="h-5 w-5 text-accent" />
          </div>
          <motion.div
            animate={{
              display: animate ? (open ? 'block' : 'none') : 'block',
              opacity: animate ? (open ? 1 : 0) : 1,
              width: animate ? (open ? 'auto' : 0) : 'auto',
            }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="font-display whitespace-nowrap text-[18px] leading-none tracking-[-0.01em] text-foreground">
              {t('brand.product')}
            </div>
            <div
              className="mt-1 whitespace-nowrap text-xs font-medium text-muted-foreground"
              title={t('brand.full')}
            >
              {t('brand.short')}
            </div>
            <div className="mt-0.5 whitespace-nowrap text-[11px] font-medium text-muted-foreground/70">
              {NODE_SERIAL}
            </div>
          </motion.div>
          <div className={cn('flex-shrink-0', expanded && 'ml-auto')}>
            <NotificationBell />
          </div>
        </div>
      </SidebarHeader>

      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
        <motion.div
          animate={{
            display: animate ? (open ? 'block' : 'none') : 'block',
            opacity: animate ? (open ? 1 : 0) : 1,
          }}
          transition={{ duration: 0.2 }}
          className="px-4 pb-2 pt-4"
        >
          <span className="text-xs font-medium text-muted-foreground">
            {t('dashboard:nav.navigationHeading')}
          </span>
        </motion.div>
        <nav className="flex flex-col gap-0.5 px-2 pb-2" aria-label={t('dashboard:nav.navigationLabel')}>
          {navItems.map((item) => (
            <SidebarLink
              key={item.label}
              link={item}
              active={
                location.pathname === item.href ||
                (item.href === '/dashboard' && location.pathname === '/')
              }
              onClick={() => onNavChange?.(item.label)}
            />
          ))}
        </nav>
      </div>

      <div className="flex-shrink-0 border-t border-border">
        <motion.div
          className={cn(
            'flex flex-col gap-2 pb-4 pt-4',
            animate && !open ? 'items-center px-2' : 'px-4',
          )}
          animate={{
            paddingLeft: animate ? (open ? '1rem' : '0.5rem') : '1rem',
            paddingRight: animate ? (open ? '1rem' : '0.5rem') : '1rem',
          }}
          transition={{ duration: 0.2 }}
        >
          {open ? (
            <div className="flex items-center justify-between gap-2">
              <ThemeToggle />
              <LanguageSwitcher variant="compact" align="right" direction="up" />
            </div>
          ) : (
            <>
              <ThemeToggle />
              <LanguageSwitcher variant="icon" align="left" direction="up" />
            </>
          )}
        </motion.div>
      </div>
    </SidebarBody>
  );
};

export default Sidebar;
