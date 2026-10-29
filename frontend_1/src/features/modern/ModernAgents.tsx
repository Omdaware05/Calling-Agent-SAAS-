import React, { useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, ArrowUpRight, Languages, Cpu, Users } from 'lucide-react';
import { clsx } from 'clsx';
import { agentsApi } from '../../services/api/agents';
import { callsApi } from '../../services/api/calls';
import type { CallDocument } from '../../types/api';
import { MCard, MPageHeader, Avatar, Pill, primaryPill } from './ui';

export const ModernAgents: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: agents = [], isLoading } = useQuery({ queryKey: ['agents'], queryFn: () => agentsApi.getAgents(50) });
  const { data: calls = [] } = useQuery<CallDocument[]>({
    queryKey: ['modern-calls'],
    queryFn: () => callsApi.getCalls({ limit: 200 }),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => agentsApi.toggleAgent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  const callsByAgent = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of calls) if (c.agent_id) map.set(c.agent_id, (map.get(c.agent_id) || 0) + 1);
    return map;
  }, [calls]);

  return (
    <div>
      <MPageHeader
        title="AI Agents"
        subtitle="Your voice agents — what they do, which business they serve, and how much they call."
        actions={
          <button type="button" className={primaryPill} onClick={() => navigate('/agents')}>
            <Plus className="w-4 h-4" /> New Agent
          </button>
        }
      />

      {isLoading && <MCard className="p-8 text-center text-sm text-[#98A2B3]">Loading agents…</MCard>}
      {!isLoading && agents.length === 0 && (
        <MCard className="p-8 text-center">
          <p className="text-sm font-semibold text-[#344054]">No agents yet</p>
          <p className="text-[13px] text-[#98A2B3] mt-1">Create your first AI agent to start making calls.</p>
        </MCard>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.map((agent, i) => (
          <MCard key={agent.agent_id} className="p-6 anim-enter">
            <div style={{ animationDelay: `${Math.min(i * 60, 300)}ms` }} className="anim-enter">
              <div className="flex items-start gap-3.5">
                <Avatar name={agent.name} className="w-12 h-12 text-base" />
                <div className="flex-1 min-w-0">
                  <p className="text-[15px] font-bold text-[#101828] truncate">{agent.name}</p>
                  <p className="text-xs text-[#98A2B3] truncate">{agent.company_name || 'ARB SoftTech'}</p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={agent.is_enabled}
                  title={agent.is_enabled ? 'Pause agent' : 'Activate agent'}
                  onClick={() => toggleMutation.mutate(agent.agent_id)}
                  className={clsx(
                    'relative w-11 h-6 rounded-full transition-colors shrink-0 mt-0.5',
                    agent.is_enabled ? 'bg-emerald-500' : 'bg-[#E4E7EC]'
                  )}
                >
                  <span
                    className={clsx(
                      'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all',
                      agent.is_enabled ? 'left-[22px]' : 'left-0.5'
                    )}
                  />
                </button>
              </div>

              <p className="text-[13px] text-[#667085] leading-relaxed mt-3.5 line-clamp-2 min-h-[36px]">
                {agent.purpose || agent.description || 'AI voice calling agent'}
              </p>

              <div className="flex flex-wrap gap-1.5 mt-3.5">
                <Pill tone="slate">
                  <Languages className="w-3 h-3" /> {agent.default_language || 'English'}
                </Pill>
                <Pill tone="slate">
                  <Cpu className="w-3 h-3" /> {agent.provider || 'vobiz'}
                </Pill>
                <Pill tone="slate">
                  <Users className="w-3 h-3" /> {agent.concurrency || 1} parallel
                </Pill>
              </div>

              <div className="flex items-center justify-between mt-5 pt-4 border-t border-[#F1F2F4]">
                <div>
                  <span className="text-lg font-bold text-[#101828] tabular-nums">{callsByAgent.get(agent.agent_id) || 0}</span>
                  <span className="text-xs text-[#98A2B3] font-medium"> calls made</span>
                </div>
                <Pill tone={agent.is_enabled ? 'emerald' : 'slate'}>{agent.is_enabled ? 'Active' : 'Paused'}</Pill>
                <button
                  type="button"
                  onClick={() => navigate(`/agents/${agent.agent_id}`)}
                  className="inline-flex items-center gap-1 text-[13px] font-semibold text-orange-600 hover:text-orange-500"
                >
                  Open <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </MCard>
        ))}
      </div>
    </div>
  );
};
