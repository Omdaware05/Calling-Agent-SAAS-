import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { MapPin, PhoneCall, Target, TrendingUp, Bot } from 'lucide-react';
import { businessesApi } from '../../services/api/businesses';
import { MCard, MPageHeader, Avatar, Pill } from './ui';

export const ModernBusinesses: React.FC = () => {
  const navigate = useNavigate();
  const { data: businesses = [], isLoading } = useQuery({
    queryKey: ['businesses'],
    queryFn: () => businessesApi.list({ limit: 100 }),
  });

  return (
    <div>
      <MPageHeader
        title="Businesses"
        subtitle="The client businesses your agents call for — performance at a glance."
      />

      {isLoading && <MCard className="p-8 text-center text-sm text-[#98A2B3]">Loading businesses…</MCard>}
      {!isLoading && businesses.length === 0 && (
        <MCard className="p-8 text-center">
          <p className="text-sm font-semibold text-[#344054]">No businesses yet</p>
          <p className="text-[13px] text-[#98A2B3] mt-1">Add a business to assign agents and start campaigns.</p>
        </MCard>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {businesses.map((b, i) => (
          <button
            key={b.business_id}
            type="button"
            onClick={() => navigate(`/businesses/${b.business_id}`)}
            className="text-left anim-enter"
            style={{ animationDelay: `${Math.min(i * 60, 300)}ms` }}
          >
            <MCard className="p-6 h-full hover:shadow-[0_2px_4px_rgba(16,24,40,0.06),0_24px_50px_-28px_rgba(16,24,40,0.3)] hover:-translate-y-0.5 transition-all">
              <div className="flex items-start gap-3.5">
                <Avatar name={b.name} className="w-12 h-12 text-base" />
                <div className="flex-1 min-w-0">
                  <p className="text-[15px] font-bold text-[#101828] truncate">{b.name}</p>
                  <p className="text-xs text-[#98A2B3] flex items-center gap-1 mt-0.5">
                    <MapPin className="w-3 h-3" /> {b.country || 'India'} · {b.timezone}
                  </p>
                </div>
                <Pill tone={b.is_active ? 'emerald' : 'slate'}>{b.is_active ? 'Active' : 'Inactive'}</Pill>
              </div>

              <div className="flex flex-wrap gap-1.5 mt-4">
                <Pill tone="amber">{b.industry || 'General'}</Pill>
                <Pill tone="slate">
                  <Bot className="w-3 h-3" /> {b.assigned_agent_ids?.length || 0} agent{(b.assigned_agent_ids?.length || 0) === 1 ? '' : 's'}
                </Pill>
              </div>

              <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-[#F1F2F4] text-center">
                <div>
                  <p className="text-base font-bold text-[#101828] tabular-nums flex items-center justify-center gap-1">
                    <PhoneCall className="w-3.5 h-3.5 text-[#98A2B3]" /> {b.total_calls ?? 0}
                  </p>
                  <p className="text-[10.5px] text-[#98A2B3] font-medium mt-0.5">Calls</p>
                </div>
                <div>
                  <p className="text-base font-bold text-[#101828] tabular-nums flex items-center justify-center gap-1">
                    <Target className="w-3.5 h-3.5 text-[#98A2B3]" /> {b.total_leads ?? 0}
                  </p>
                  <p className="text-[10.5px] text-[#98A2B3] font-medium mt-0.5">Leads</p>
                </div>
                <div>
                  <p className="text-base font-bold text-emerald-600 tabular-nums flex items-center justify-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" /> {Math.round(b.conversion_rate ?? 0)}%
                  </p>
                  <p className="text-[10.5px] text-[#98A2B3] font-medium mt-0.5">Conversion</p>
                </div>
              </div>
            </MCard>
          </button>
        ))}
      </div>
    </div>
  );
};
