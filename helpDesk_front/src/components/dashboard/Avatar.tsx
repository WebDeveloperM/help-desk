import type { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { useSidebar } from '@/components/ui/sidebar';
import { cn } from '@/lib/utils';

interface AvatarProps {
  name: string;
  role: string;
  image?: string;
  online?: boolean;
}

const Avatar = ({ name, role, image, online = false }: AvatarProps): JSX.Element => {
  const { open, animate } = useSidebar();
  const { t } = useTranslation('common');

  return (
    <div
      className={cn(
        "flex items-center gap-3 py-2 px-2 rounded-xl hover:bg-secondary transition-colors",
        animate && !open && "justify-center"
      )}
      role="listitem"
      aria-label={`${name}, ${role}${online ? `, ${t('avatar.online')}` : ''}`}
    >
      <div className="relative flex-shrink-0" aria-hidden>
        {image ? (
          <img
            src={image}
            alt=""
            className="w-9 h-9 rounded-full object-cover bg-muted border border-border"
          />
        ) : (
          <div className="w-9 h-9 rounded-full bg-muted border border-border" />
        )}
        {online && (
          <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-accent rounded-full border-2 border-card" />
        )}
      </div>
      <motion.div 
        className="flex-1 min-w-0"
        animate={{
          display: animate ? (open ? "block" : "none") : "block",
          opacity: animate ? (open ? 1 : 0) : 1,
          width: animate ? (open ? "auto" : 0) : "auto",
        }}
        transition={{ duration: 0.2 }}
      >
        <div className="text-sm font-medium text-foreground truncate">{name}</div>
        <div className="text-xs text-muted-foreground truncate">{role}</div>
      </motion.div>
    </div>
  );
};

export default Avatar;
