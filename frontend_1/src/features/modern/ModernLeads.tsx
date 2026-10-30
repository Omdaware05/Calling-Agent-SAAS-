import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Download, MapPin, Wallet, PhoneForwarded, Users, Heart, BadgeCheck, PhoneOff } from 'lucide-react';
import { clsx } from 'clsx';
import { leadsApi } from '../../services/api/leads';
import type { LeadDocument } from '../../types/api';
import { MCard, MStatCard, MPageHeader, Avatar, Pill, ScoreBar, scorePct, leadStatusMeta, timeAgo, whitePill } from './ui';

const FILTERS = [
  { id: 'all', label: 'All Leads' },
  { id: 'interested', label: 'Interested' },
  { id: 'qualified', label: 'Qualified' },
  { id: 'new', label: 'New' },
  { id: 'not_interested', label: 'Not Interested' },
  { id: 'closed', label: 'Closed' },
] as const;

export const ModernLeads: React.FC = () => {
  const [filter, setFilter] = useState<string>('all');
  const [query, setQuery] = useState('');

  const { data: leads = [], isLoading } = useQuery<LeadDocument[]>({
    queryKey: ['leads'],
    queryFn: () => leadsApi.getLeads({ limit: 500 }),
    refetchInterval: 15000,
  });

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const l of leads) map.set((l.status || 'new').toLowerCase(), (map.get((l.status || 'new').toLowerCase()) || 0) + 1);
    return map;
  }, [leads]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return leads.filter((l) => {
      if (filter !== 'all' && (l.status || '').toLowerCase() !== filter) return false;
      if (!q) return true;
      const info = l.metadata?.customer_info;
      return [l.name, l.phone_number, l.email, info?.city]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q));
    });
  }, [leads, filter, query]);

  const stats = [
    { label: 'Total Leads', value: leads.length.toLocaleString('en-IN'), icon: Users, iconClass: 'bg-[#F2F4F7] text-[#344054]', subtext: 'captured by AI callers' },
    { label: 'Interested', value: (counts.get('interested') || 0).toLocaleString('en-IN'), icon: Heart, iconClass: 'bg-[#E7F8EE] text-[#16A34A]', subtext: leads.length ? `${Math.round(((counts.get('interested') || 0) / leads.length) * 100)}% of all leads` : '' },
    { label: 'Qualified', value: (counts.get('qualified') || 0).toLocaleString('en-IN'), icon: BadgeCheck, iconClass: 'bg-[#F1EAFE] text-[#7C3AED]', subtext: 'ready for sales follow-up' },
    { label: 'Not Interested', value: (counts.get('not_interested') || 0).toLocaleString('en-IN'), icon: PhoneOff, iconClass: 'bg-[#FDECEC] text-[#DC2626]', subtext: 'excluded from calling' },
  ];

  return (
    <div>
      <MPageHeader
        title="Leads"
        subtitle="Every lead captured by your AI callers — with the customer details and the reason, straight from the call."
        actions={
          <>
            <button type="button" className={whitePill} onClick={() => leadsApi.downloadLeadsExcel().catch(() => {})}>
              <Download className="w-4 h-4" /> All Leads (Excel)
            </button>
            <button
              type="button"
              className={whitePill}
              onClick={() => leadsApi.downloadLeadsExcel('interested').catch(() => {})}
            >
              <Download className="w-4 h-4" /> Interested Only
            </button>
          </>
        }
      />

      {/* Stat strip (design #2) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
        {stats.map((st, i) => (
          <MStatCard key={st.label} {...st} delay={i * 60} />
        ))}
      </div>

      {/* Filter pills + search */}
      <div className="flex flex-wrap items-center gap-2.5 mb-6">
        <div className="flex flex-wrap gap-1.5">
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
              {f.id !== 'all' && (counts.get(f.id) || 0) > 0 && (
                <span className={clsx('ml-1.5 tabular-nums', filter === f.id ? 'text-white/60' : 'text-[#C4CBD4]')}>
                  {counts.get(f.id)}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="relative ml-auto w-full sm:w-72">
          <Search className="w-4 h-4 text-[#98A2B3] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, phone, email, city…"
            className="w-full h-10 pl-10 pr-4 rounded-full bg-white border border-[#E8EAED] text-[13px] placeholder-[#98A2B3] focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-500/15 transition-all"
          />
        </div>
      </div>

      {/* Lead cards */}
      <div className="space-y-3.5">
        {isLoading && <MCard className="p-8 text-center text-sm text-[#98A2B3]">Loading leads…</MCard>}
        {!isLoading && visible.length === 0 && (
          <MCard className="p-8 text-center">
            <p className="text-sm font-semibold text-[#344054]">No leads match this view</p>
            <p className="text-[13px] text-[#98A2B3] mt-1">Try a different filter or search term.</p>
          </MCard>
        )}
        {visible.map((lead, idx) => {
          const info = lead.metadata?.customer_info;
          const why = lead.metadata?.why_interested || [];
          const whyNot = lead.metadata?.why_not_interested || [];
          const meta = leadStatusMeta(lead.status);
          return (
            <MCard key={lead.lead_id} className="p-5 anim-row" >
              <div style={{ animationDelay: `${Math.min(idx * 45, 360)}ms` }} className="flex flex-wrap items-start gap-4">
                <Avatar name={lead.name || lead.phone_number} className="w-11 h-11 text-sm" />
                <div className="flex-1 min-w-[220px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[15px] font-bold text-[#101828]">{lead.name || 'Unknown caller'}</p>
                    <Pill tone={meta.tone}>{meta.label}</Pill>
                    <span className="text-xs text-[#98A2B3]">{timeAgo(lead.created_at)}</span>
                  </div>
                  <p className="text-[13px] text-[#667085] mt-0.5">
                    {lead.phone_number}
                    {lead.email ? ` · ${lead.email}` : ''}
                  </p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-[#667085]">
                    {info?.city && (
                      <span className="inline-flex items-center gap-1"><MapPin className="w-3.5 h-3.5 text-[#98A2B3]" /> {info.city}</span>
                    )}
                    {info?.budget_inr ? (
                      <span className="inline-flex items-center gap-1"><Wallet className="w-3.5 h-3.5 text-[#98A2B3]" /> Budget ₹{info.budget_inr.toLocaleString('en-IN')}</span>
                    ) : null}
                    {info?.preferred_callback_time && (
                      <span className="inline-flex items-center gap-1"><PhoneForwarded className="w-3.5 h-3.5 text-[#98A2B3]" /> Callback: {info.preferred_callback_time}</span>
                    )}
                  </div>
                  {(why.length > 0 || whyNot.length > 0) && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {why.slice(0, 3).map((r, i) => (
                        <span key={`w${i}`} title={r.evidence || undefined} className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200/70 text-emerald-700 text-[11px] font-semibold">
                          {r.reason}
                        </span>
                      ))}
                      {whyNot.slice(0, 3).map((r, i) => (
                        <span key={`n${i}`} title={r.evidence || undefined} className="px-2.5 py-1 rounded-full bg-rose-50 border border-rose-200/70 text-rose-700 text-[11px] font-semibold">
                          {r.reason}
                        </span>
                      ))}
                    </div>
                  )}
                  {lead.reasoning && (
                    <p className="text-xs text-[#98A2B3] mt-2.5 leading-relaxed max-w-2xl">{lead.reasoning}</p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[#98A2B3]">Interest score</span>
                  <ScoreBar value={scorePct(lead.confidence_score ?? lead.score)} />
                </div>
              </div>
            </MCard>
          );
        })}
      </div>
    </div>
  );
};
