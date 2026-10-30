import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PhoneOutgoing, ChevronRight, PhoneCall, Radio, PhoneMissed } from 'lucide-react';
import { clsx } from 'clsx';
import { callsApi } from '../../services/api/calls';
import { agentsApi } from '../../services/api/agents';
import { statsApi } from '../../services/api/stats';
import type { CallDocument } from '../../types/api';
import { MCard, MStatCard, MPageHeader, Pill, callStateMeta, fmtDuration, timeAgo } from './ui';
import { parseServerDate } from '../../utils/dateUtils';

const FILTERS = [
  { id: 'all', label: 'All Calls' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'FAILED', label: 'Failed' },
  { id: 'BUSY', label: 'Busy' },
  { id: 'NO_ANSWER', label: 'No Answer' },
  { id: 'live', label: 'Live Now' },
] as const;

const LIVE_STATES = ['QUEUED', 'DIALING', 'RINGING', 'CONNECTED', 'LISTENING', 'THINKING', 'SPEAKING'];

export const ModernCalls: React.FC = () => {
  const [filter, setFilter] = useState<string>('all');

  const { data: stats } = useQuery({ queryKey: ['global-stats'], queryFn: statsApi.getStats, refetchInterval: 15000 });
  const { data: calls = [], isLoading } = useQuery<CallDocument[]>({
    queryKey: ['modern-calls'],
    queryFn: () => callsApi.getCalls({ limit: 200 }),
    refetchInterval: 15000,
  });
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: () => agentsApi.getAgents(50) });

  const agentName = useMemo(() => {
    const map = new Map(agents.map((a) => [a.agent_id, a.name]));
    return (id?: string | null) => (id && map.get(id)) || 'AI Agent';
  }, [agents]);

  const visible = useMemo(() => {
    const sorted = [...calls].sort((a, b) => (parseServerDate(b.created_at)?.getTime() || 0) - (parseServerDate(a.created_at)?.getTime() || 0));
    if (filter === 'all') return sorted;
    if (filter === 'live') return sorted.filter((c) => LIVE_STATES.includes(c.state));
    return sorted.filter((c) => c.state === filter);
  }, [calls, filter]);

  const statCards = [
    { label: 'Total Calls', value: (stats?.total_calls ?? calls.length).toLocaleString('en-IN'), icon: PhoneCall, iconClass: 'bg-[#FFF1E6] text-[#EA580C]', subtext: 'across all agents' },
    { label: 'Live Now', value: (stats?.active ?? 0).toLocaleString('en-IN'), icon: Radio, iconClass: 'bg-[#E7F8EE] text-[#16A34A]', subtext: 'calls in progress' },
    { label: 'Completed', value: (stats?.completed ?? 0).toLocaleString('en-IN'), icon: PhoneOutgoing, iconClass: 'bg-[#E6F4FE] text-[#0284C7]', subtext: stats?.total_calls ? `${Math.round(((stats?.completed ?? 0) / stats.total_calls) * 100)}% of all calls` : '' },
    { label: 'Failed', value: (stats?.failed ?? 0).toLocaleString('en-IN'), icon: PhoneMissed, iconClass: 'bg-[#FDECEC] text-[#DC2626]', subtext: 'could not connect' },
  ];

  return (
    <div>
      <MPageHeader title="Calls" subtitle="Every conversation your AI agents have had — newest first." />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
        {statCards.map((st, i) => (
          <MStatCard key={st.label} {...st} delay={i * 60} />
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-6">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => setFilter(f.id)}
            className={clsx(
              'h-9 px-4 rounded-full text-xs font-semibold transition-all',
              filter === f.id
                ? 'bg-[#101828] text-white shadow-[0_1px_2px_rgba(16,24,40,0.25)]'
                : 'bg-white border border-[#E4E7EC] text-[#667085] hover:text-[#101828]'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <MCard className="overflow-hidden">
        {isLoading && <p className="p-8 text-center text-sm text-[#98A2B3]">Loading calls…</p>}
        {!isLoading && visible.length === 0 && (
          <p className="p-8 text-center text-sm text-[#98A2B3]">No calls in this view yet.</p>
        )}
        <div className="divide-y divide-[#F1F2F4]">
          {visible.slice(0, 30).map((call) => {
            const meta = callStateMeta(call.state);
            const interest = (call.last_interest_status || '').toLowerCase();
            return (
              <div key={call.call_id} className="flex items-center gap-4 px-5 sm:px-6 py-4 hover:bg-[#FAFAFB] transition-colors">
                <span className="w-10 h-10 rounded-full bg-orange-50 border border-orange-100 flex items-center justify-center shrink-0">
                  <PhoneOutgoing className="w-[18px] h-[18px] text-orange-600" strokeWidth={1.9} />
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-[#101828] tabular-nums">{call.phone_number}</p>
                  <p className="text-xs text-[#98A2B3] truncate">
                    {agentName(call.agent_id)} · {timeAgo(call.created_at)}
                  </p>
                </div>
                {interest && (
                  <span className="hidden md:block">
                    <Pill tone={interest === 'interested' ? 'emerald' : interest === 'not_interested' ? 'rose' : 'amber'}>
                      {interest.replace(/_/g, ' ')}
                    </Pill>
                  </span>
                )}
                <span className="hidden sm:block text-[13px] font-semibold text-[#344054] tabular-nums w-16 text-right">
                  {fmtDuration(call.duration)}
                </span>
                <Pill tone={meta.tone}>{meta.label}</Pill>
                <ChevronRight className="w-4 h-4 text-[#C4CBD4] shrink-0" />
              </div>
            );
          })}
        </div>
        {visible.length > 30 && (
          <p className="px-6 py-3.5 text-xs text-[#98A2B3] border-t border-[#F1F2F4]">
            Showing the 30 most recent of {visible.length} calls.
          </p>
        )}
      </MCard>
    </div>
  );
};
