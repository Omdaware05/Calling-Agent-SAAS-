import React from 'react';
import { clsx } from 'clsx';
import { Info, ArrowUp, ArrowDown } from 'lucide-react';
import { parseServerDate } from '../../utils/dateUtils';

/**
 * Shared building blocks for the Modern experience.
 * Design language: soft gray canvas, solid white cards (24px radius),
 * hairline borders, one accent (brand orange), pill controls.
 */

export const MCard: React.FC<{ className?: string; children: React.ReactNode }> = ({
  className,
  children,
}) => (
  <div
    className={clsx(
      'bg-white border border-slate-200/90 rounded-xl shadow-xs',
      className
    )}
  >
    {children}
  </div>
);

/**
 * Stat card matching the enterprise operational telemetry theme.
 */
export const MStatCard: React.FC<{
  label: string;
  value: string;
  icon: React.ElementType;
  iconClass?: string;
  deltaPct?: number | null;
  deltaCaption?: string;
  subtext?: string;
  delay?: number;
}> = ({ label, value, icon: Icon, iconClass = 'bg-slate-50 text-slate-700 border border-slate-200', deltaPct, deltaCaption = 'vs previous 7 days', subtext, delay = 0 }) => (
  <MCard className="p-4 sm:p-5">
    <div className="anim-enter" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={clsx('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', iconClass)}>
            <Icon className="w-4 h-4" strokeWidth={2} />
          </span>
          <p className="font-label-sm uppercase tracking-wider text-slate-500 text-[11px] font-semibold">{label}</p>
        </div>
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
      </div>
      <p className="font-headline-md text-slate-900 text-2xl font-bold tracking-tight mt-3 tabular-nums">{value}</p>
      <div className="flex items-center gap-2 mt-2 min-h-[20px]">
        {deltaPct !== undefined && deltaPct !== null && isFinite(deltaPct) ? (
          <>
            <span
              className={clsx(
                'inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[11px] font-mono-sm font-medium',
                deltaPct >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
              )}
            >
              {deltaPct >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
              {Math.abs(deltaPct).toFixed(0)}%
            </span>
            <span className="text-xs text-slate-500">{deltaCaption}</span>
          </>
        ) : (
          <span className="text-xs text-slate-500">{subtext || ''}</span>
        )}
      </div>
    </div>
  </MCard>
);

export const MPageHeader: React.FC<{
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}> = ({ title, subtitle, actions }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-5 anim-enter">
    <div>
      <h1 className="font-headline-md text-xl sm:text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
      {subtitle && <p className="font-body-sm text-xs sm:text-sm text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
    {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
  </div>
);

export const primaryPill =
  'inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900 text-white rounded-md font-label-md text-xs hover:bg-slate-800 transition-all font-medium shadow-xs';
export const whitePill =
  'inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-white border border-slate-200 text-slate-700 hover:text-slate-900 hover:bg-slate-50 rounded-md font-label-md text-xs transition-colors font-medium shadow-xs';

const AVATAR_BG = [
  'bg-orange-100 text-orange-700',
  'bg-emerald-100 text-emerald-700',
  'bg-sky-100 text-sky-700',
  'bg-violet-100 text-violet-700',
  'bg-rose-100 text-rose-700',
  'bg-amber-100 text-amber-700',
];

export const Avatar: React.FC<{ name?: string | null; className?: string }> = ({
  name,
  className,
}) => {
  const label = (name || 'Unknown').trim();
  const initials = label
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('') || '?';
  const idx = label.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_BG.length;
  return (
    <div
      className={clsx(
        'rounded-full flex items-center justify-center font-semibold shrink-0 w-10 h-10 text-[13px]',
        AVATAR_BG[idx],
        className
      )}
      aria-hidden="true"
    >
      {initials}
    </div>
  );
};

type Tone = 'emerald' | 'rose' | 'amber' | 'sky' | 'slate' | 'violet';
const TONES: Record<Tone, string> = {
  emerald: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200/70 dark:border-emerald-500/20',
  rose: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200/70 dark:border-rose-500/20',
  amber: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200/70 dark:border-amber-500/20',
  sky: 'bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-200/70 dark:border-sky-500/20',
  slate: 'bg-slate-100 dark:bg-white/[0.06] text-slate-600 dark:text-neutral-300 border-slate-200 dark:border-white/[0.1]',
  violet: 'bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-400 border-violet-200/70 dark:border-violet-500/20',
};

export const Pill: React.FC<{ tone?: Tone; children: React.ReactNode; className?: string }> = ({
  tone = 'slate',
  children,
  className,
}) => (
  <span
    className={clsx(
      'inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-semibold whitespace-nowrap',
      TONES[tone],
      className
    )}
  >
    {children}
  </span>
);

export function leadStatusMeta(status?: string | null): { label: string; tone: Tone } {
  switch ((status || '').toLowerCase()) {
    case 'interested':
      return { label: 'Interested', tone: 'emerald' };
    case 'qualified':
      return { label: 'Qualified', tone: 'violet' };
    case 'not_interested':
      return { label: 'Not Interested', tone: 'rose' };
    case 'closed':
      return { label: 'Closed', tone: 'slate' };
    case 'new':
      return { label: 'New', tone: 'amber' };
    default:
      return { label: (status || 'New').replace(/_/g, ' '), tone: 'sky' };
  }
}

export function callStateMeta(state?: string | null): { label: string; tone: Tone } {
  switch ((state || '').toUpperCase()) {
    case 'COMPLETED':
      return { label: 'Completed', tone: 'emerald' };
    case 'FAILED':
      return { label: 'Failed', tone: 'rose' };
    case 'BUSY':
      return { label: 'Busy', tone: 'amber' };
    case 'NO_ANSWER':
      return { label: 'No Answer', tone: 'slate' };
    case 'QUEUED':
      return { label: 'Queued', tone: 'sky' };
    case 'HANGUP':
      return { label: 'Hangup', tone: 'slate' };
    default:
      return { label: 'Live', tone: 'emerald' };
  }
}

export const ScoreBar: React.FC<{ value: number }> = ({ value }) => {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  const color = v >= 70 ? 'bg-emerald-500' : v >= 40 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[#EEF1F4] overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all duration-700', color)} style={{ width: `${v}%` }} />
      </div>
      <span className="text-xs font-semibold text-[#344054] tabular-nums">{v}%</span>
    </div>
  );
};

/** Lead scores arrive as a 0–1 fraction from the API; normalize to 0–100. */
export function scorePct(raw?: number | null): number {
  const v = raw ?? 0;
  return v <= 1 ? v * 100 : v;
}

export function fmtDuration(totalSeconds?: number | null): string {
  const s = Math.max(0, Math.round(totalSeconds || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m}m ${String(r).padStart(2, '0')}s` : `${r}s`;
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return '';
  const d = parseServerDate(iso);
  if (!d) return '';
  const then = d.getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? '1 day ago' : `${days} days ago`;
}

export const MEmpty: React.FC<{ title: string; text?: string }> = ({ title, text }) => (
  <div className="py-12 text-center">
    <p className="text-sm font-semibold text-[#344054] dark:text-neutral-300">{title}</p>
    {text && <p className="text-[13px] text-[#667085] dark:text-neutral-400 mt-1">{text}</p>}
  </div>
);
