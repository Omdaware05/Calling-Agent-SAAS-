import React from 'react';
import { clsx } from 'clsx';
import { Card } from './Card';
import { Skeleton } from './Skeleton';

export interface MetricCardProps {
  label: string;
  value: string | number | React.ReactNode;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    positive?: boolean;
  };
  isLoading?: boolean;
  className?: string;
  glow?: boolean;
  tilt?: boolean;
  stars?: boolean;
  magnetism?: boolean;
  ripple?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon,
  trend,
  isLoading = false,
  className,
  glow = true,
  tilt = true,
  stars = true,
  magnetism = false,
  ripple = true,
}) => {
  return (
    <Card
      glow={glow}
      tilt={tilt}
      stars={stars}
      magnetism={magnetism}
      ripple={ripple}
      className={clsx('flex flex-col justify-between cursor-default', className)}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          {icon && (
            <div className="w-8 h-8 rounded-xl bg-orange-500/15 text-orange-400 border border-orange-500/20 flex items-center justify-center shrink-0">
              {icon}
            </div>
          )}
          <span className="text-[13px] font-medium text-slate-600 dark:text-[#C9C9D1] truncate">
            {label}
          </span>
        </div>
        {trend && (
          <span
            className={clsx(
              'px-2.5 py-0.5 rounded-full text-[12px] font-semibold tabular-nums shrink-0 border',
              trend.positive
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-neutral-800/80 text-neutral-300 border-white/[0.10]'
            )}
          >
            {trend.value}
          </span>
        )}
      </div>

      <div className="mt-3">
        {isLoading ? (
          <Skeleton height={32} width={70} />
        ) : (
          <div className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-[#F8F8FA] tabular-nums">
            {value}
          </div>
        )}
      </div>

      {subtext && (
        <p className="mt-1.5 text-[12.5px] text-slate-500 dark:text-[#C9C9D1] truncate font-normal">
          {subtext}
        </p>
      )}
    </Card>
  );
};
