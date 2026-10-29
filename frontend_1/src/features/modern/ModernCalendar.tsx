import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, PhoneCall, Target, CalendarClock, CalendarDays } from 'lucide-react';
import { calendarApi } from '../../services/api/calendar';
import { agentsApi } from '../../services/api/agents';
import { MCard, MPageHeader, Pill, callStateMeta, leadStatusMeta, fmtDuration, scorePct } from './ui';
import { clsx } from 'clsx';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function isoOf(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function timeOf(iso?: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
}

export const ModernCalendar: React.FC = () => {
  const today = useMemo(() => new Date(), []);
  const [cursor, setCursor] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [selected, setSelected] = useState<string>(isoOf(today));

  const year = cursor.getFullYear();
  const month = cursor.getMonth() + 1;

  const { data: summary } = useQuery({
    queryKey: ['calendar-summary', year, month],
    queryFn: () => calendarApi.getSummary(year, month),
  });
  const { data: day, isLoading: dayLoading } = useQuery({
    queryKey: ['calendar-day', selected],
    queryFn: () => calendarApi.getDay(selected),
  });
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: () => agentsApi.getAgents(50) });
  const agentName = useMemo(() => new Map(agents.map((a) => [a.agent_id, a.name])), [agents]);

  // 6-week grid starting on the Monday of the week containing the 1st.
  const cells = useMemo(() => {
    const first = new Date(year, month - 1, 1);
    const startOffset = (first.getDay() + 6) % 7; // Monday-first
    const start = new Date(year, month - 1, 1 - startOffset);
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      const iso = isoOf(d);
      return { date: d, iso, inMonth: d.getMonth() === month - 1, counts: summary?.days[iso] };
    });
  }, [cursor, summary]); // eslint-disable-line react-hooks/exhaustive-deps

  const moveMonth = (delta: number) => setCursor(new Date(year, month - 1 + delta, 1));
  const monthLabel = cursor.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  const selectedLabel = new Date(selected + 'T00:00:00').toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div>
      <MPageHeader
        title="Calendar"
        subtitle="What happened on any date — calls made, leads captured, and follow-ups due."
        actions={
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => moveMonth(-1)}
              className="w-10 h-10 rounded-full bg-white border border-[#E4E7EC] flex items-center justify-center text-[#344054] hover:bg-[#F9FAFB] transition-colors"
              aria-label="Previous month"
            >
              <ChevronLeft className="w-4.5 h-4.5" />
            </button>
            <button
              type="button"
              onClick={() => {
                setCursor(new Date(today.getFullYear(), today.getMonth(), 1));
                setSelected(isoOf(today));
              }}
              className="h-10 px-4 rounded-full bg-white border border-[#E4E7EC] text-[13px] font-bold text-[#344054] hover:bg-[#F9FAFB] transition-colors"
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => moveMonth(1)}
              className="w-10 h-10 rounded-full bg-white border border-[#E4E7EC] flex items-center justify-center text-[#344054] hover:bg-[#F9FAFB] transition-colors"
              aria-label="Next month"
            >
              <ChevronRight className="w-4.5 h-4.5" />
            </button>
          </div>
        }
      />

      <MCard className="overflow-hidden mb-6">
        <div className="px-6 pt-5 pb-4 flex items-center gap-2.5">
          <span className="w-9 h-9 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center">
            <CalendarDays className="w-[18px] h-[18px] text-orange-600" strokeWidth={1.9} />
          </span>
          <h3 className="text-[17px] font-extrabold tracking-tight text-[#101828]">{monthLabel}</h3>
        </div>
        <div className="grid grid-cols-7 border-t border-[#F1F2F4]">
          {WEEKDAYS.map((w) => (
            <div key={w} className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-[#98A2B3] border-b border-[#F1F2F4]">
              {w}
            </div>
          ))}
          {cells.map((cell) => {
            const isToday = cell.iso === isoOf(today);
            const isSelected = cell.iso === selected;
            const c = cell.counts;
            return (
              <button
                key={cell.iso}
                type="button"
                onClick={() => setSelected(cell.iso)}
                className={clsx(
                  'h-[104px] p-2.5 text-left align-top border-b border-r border-[#F5F6F7] transition-colors [&:nth-child(7n)]:border-r-0',
                  cell.inMonth ? 'bg-white hover:bg-[#FAFAFB]' : 'bg-[#FBFBFC]',
                  isSelected && 'bg-orange-50/60 hover:bg-orange-50/60'
                )}
              >
                <span
                  className={clsx(
                    'inline-flex w-7 h-7 items-center justify-center rounded-full text-[13px] font-bold tabular-nums',
                    isToday ? 'bg-[#101828] text-white' : cell.inMonth ? 'text-[#344054]' : 'text-[#C4CBD4]',
                    isSelected && !isToday && 'ring-2 ring-orange-400'
                  )}
                >
                  {cell.date.getDate()}
                </span>
                {c && (c.calls > 0 || c.leads > 0 || c.followups > 0) && (
                  <span className="mt-1.5 space-y-1 block">
                    {c.calls > 0 && (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-[#667085]">
                        <span className="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0" />
                        {c.calls} call{c.calls === 1 ? '' : 's'}
                      </span>
                    )}
                    {c.leads > 0 && (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-[#667085]">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                        {c.leads} lead{c.leads === 1 ? '' : 's'}
                      </span>
                    )}
                    {c.followups > 0 && (
                      <span className="flex items-center gap-1 text-[11px] font-semibold text-[#667085]">
                        <span className="w-1.5 h-1.5 rounded-full bg-violet-500 shrink-0" />
                        {c.followups} due
                      </span>
                    )}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </MCard>

      <h3 className="text-[16px] font-extrabold tracking-tight text-[#101828] mb-3">{selectedLabel}</h3>
      {dayLoading && <MCard className="p-8 text-center text-sm text-[#98A2B3]">Loading the day…</MCard>}
      {!dayLoading && day && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <MCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <PhoneCall className="w-4 h-4 text-orange-600" />
              <h4 className="text-sm font-bold text-[#101828]">Calls ({day.calls.length})</h4>
            </div>
            <div className="space-y-3">
              {day.calls.length === 0 && <p className="text-[13px] text-[#98A2B3]">No calls on this date.</p>}
              {day.calls.slice(0, 8).map((c) => {
                const meta = callStateMeta(c.state);
                return (
                  <div key={c.call_id} className="flex items-center gap-2.5">
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-bold text-[#101828] tabular-nums truncate">{c.phone_number}</p>
                      <p className="text-[11px] text-[#98A2B3] truncate">
                        {timeOf(c.created_at)} · {(c.agent_id && agentName.get(c.agent_id)) || 'AI Agent'} · {fmtDuration(c.duration)}
                      </p>
                    </div>
                    <Pill tone={meta.tone}>{meta.label}</Pill>
                  </div>
                );
              })}
              {day.calls.length > 8 && <p className="text-[11px] text-[#98A2B3]">+ {day.calls.length - 8} more calls</p>}
            </div>
          </MCard>

          <MCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-4 h-4 text-emerald-600" />
              <h4 className="text-sm font-bold text-[#101828]">Leads ({day.leads.length})</h4>
            </div>
            <div className="space-y-3">
              {day.leads.length === 0 && <p className="text-[13px] text-[#98A2B3]">No leads captured on this date.</p>}
              {day.leads.slice(0, 8).map((l) => {
                const meta = leadStatusMeta(l.status || 'new');
                return (
                  <div key={l.lead_id} className="flex items-center gap-2.5">
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-bold text-[#101828] truncate">{l.name || 'Unknown caller'}</p>
                      <p className="text-[11px] text-[#98A2B3] tabular-nums truncate">
                        {l.phone_number} · score {Math.round(scorePct(l.score))}
                      </p>
                    </div>
                    <Pill tone={meta.tone}>{meta.label}</Pill>
                  </div>
                );
              })}
              {day.leads.length > 8 && <p className="text-[11px] text-[#98A2B3]">+ {day.leads.length - 8} more leads</p>}
            </div>
          </MCard>

          <MCard className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <CalendarClock className="w-4 h-4 text-violet-600" />
              <h4 className="text-sm font-bold text-[#101828]">Follow-ups due ({day.followups.length})</h4>
            </div>
            <div className="space-y-3">
              {day.followups.length === 0 && <p className="text-[13px] text-[#98A2B3]">No follow-ups due on this date.</p>}
              {day.followups.slice(0, 8).map((f) => (
                <div key={f.followup_id} className="flex items-center gap-2.5">
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-bold text-[#101828] tabular-nums truncate">{f.phone_number}</p>
                    <p className="text-[11px] text-[#98A2B3] truncate">
                      {timeOf(f.scheduled_at)} · {f.notes || 'Scheduled callback'}
                    </p>
                  </div>
                  <Pill tone={f.status === 'completed' ? 'emerald' : f.status === 'cancelled' ? 'rose' : 'amber'}>
                    {f.status === 'completed' ? 'Done' : f.status === 'cancelled' ? 'Cancelled' : 'Pending'}
                  </Pill>
                </div>
              ))}
              {day.followups.length > 8 && <p className="text-[11px] text-[#98A2B3]">+ {day.followups.length - 8} more follow-ups</p>}
            </div>
          </MCard>
        </div>
      )}
    </div>
  );
};
