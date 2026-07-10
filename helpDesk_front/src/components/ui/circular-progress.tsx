import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

type CircularProgressProps = {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  trackClassName?: string;
  progressClassName?: string;
  showLabel?: boolean;
};

const clampProgress = (value: number): number => {
  if (Number.isNaN(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value)));
};

export const CircularProgress = ({
  value,
  size = 56,
  strokeWidth = 6,
  className,
  trackClassName,
  progressClassName,
  showLabel = true,
}: CircularProgressProps) => {
  const { t } = useTranslation('tickets');
  const progress = clampProgress(value);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;
  const center = size / 2;

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      aria-label={t('progress.aria', { value: progress })}
      role="img"
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          className={cn('stroke-muted', trackClassName)}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${center} ${center})`}
          className={cn('stroke-accent transition-[stroke-dashoffset] duration-300', progressClassName)}
        />
      </svg>
      {showLabel && (
        <span className="absolute text-xs font-semibold text-foreground">
          {progress}%
        </span>
      )}
    </div>
  );
};
