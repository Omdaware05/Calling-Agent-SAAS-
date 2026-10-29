import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Users, PhoneCall, Heart, UserPlus } from 'lucide-react';
import { contactsApi } from '../../services/api/contacts';
import type { ContactDocument } from '../../types/api';
import { MCard, MStatCard, MPageHeader, Avatar, Pill, timeAgo } from './ui';

export const ModernContacts: React.FC = () => {
  const [query, setQuery] = useState('');
  const { data: contacts = [], isLoading } = useQuery<ContactDocument[]>({
    queryKey: ['contacts'],
    queryFn: () => contactsApi.getContacts({ limit: 200 }),
  });

  const called = contacts.filter((c) => (c.interaction_count || 0) > 0).length;
  const interested = contacts.filter((c) => (c.last_interest_status || '').toLowerCase() === 'interested').length;
  const weekAgo = Date.now() - 7 * 24 * 3600 * 1000;
  const fresh = contacts.filter((c) => new Date(c.created_at).getTime() > weekAgo).length;

  const stats = [
    { label: 'Total Contacts', value: contacts.length.toLocaleString('en-IN'), icon: Users, iconClass: 'bg-[#F2F4F7] text-[#344054]', subtext: 'in your address book' },
    { label: 'Called at Least Once', value: called.toLocaleString('en-IN'), icon: PhoneCall, iconClass: 'bg-[#E6F4FE] text-[#0284C7]', subtext: contacts.length ? `${Math.round((called / contacts.length) * 100)}% of contacts` : '' },
    { label: 'Interested Contacts', value: interested.toLocaleString('en-IN'), icon: Heart, iconClass: 'bg-[#E7F8EE] text-[#16A34A]', subtext: 'showed buying interest' },
    { label: 'Added This Week', value: fresh.toLocaleString('en-IN'), icon: UserPlus, iconClass: 'bg-[#FFF1E6] text-[#EA580C]', subtext: 'new contacts' },
  ];

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return contacts;
    return contacts.filter((c) =>
      [c.name, c.phone_number, c.email].filter(Boolean).some((v) => String(v).toLowerCase().includes(q))
    );
  }, [contacts, query]);

  return (
    <div>
      <MPageHeader
        title="Contacts"
        subtitle="Everyone your agents can call — with their call history and interest at a glance."
        actions={
          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-[#98A2B3] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search contacts…"
              className="w-full h-10 pl-10 pr-4 rounded-full bg-white border border-[#E8EAED] text-[13px] placeholder-[#98A2B3] focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-500/15 transition-all"
            />
          </div>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
        {stats.map((st, i) => (
          <MStatCard key={st.label} {...st} delay={i * 60} />
        ))}
      </div>

      <MCard className="overflow-hidden">
        {isLoading && <p className="p-8 text-center text-sm text-[#98A2B3]">Loading contacts…</p>}
        {!isLoading && visible.length === 0 && (
          <p className="p-8 text-center text-sm text-[#98A2B3]">No contacts found. Import a list or add contacts to get started.</p>
        )}
        <div className="divide-y divide-[#F1F2F4]">
          {visible.map((c) => {
            const interest = (c.last_interest_status || '').toLowerCase();
            return (
              <div key={c.contact_id} className="flex items-center gap-4 px-6 py-4 hover:bg-[#FAFAFB] transition-colors">
                <Avatar name={c.name || c.phone_number} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-[#101828] truncate">{c.name || 'Unnamed contact'}</p>
                  <p className="text-xs text-[#98A2B3] truncate">
                    {c.phone_number}
                    {c.email ? ` · ${c.email}` : ''}
                  </p>
                </div>
                <span className="hidden sm:block text-[13px] text-[#667085] font-medium tabular-nums">
                  {c.interaction_count || 0} call{(c.interaction_count || 0) === 1 ? '' : 's'}
                </span>
                <span className="hidden md:block text-xs text-[#98A2B3] w-20 text-right">{timeAgo(c.updated_at)}</span>
                {interest ? (
                  <Pill tone={interest === 'interested' ? 'emerald' : interest === 'not_interested' ? 'rose' : 'amber'}>
                    {interest.replace(/_/g, ' ')}
                  </Pill>
                ) : (
                  <Pill tone="slate">Not called</Pill>
                )}
              </div>
            );
          })}
        </div>
      </MCard>
    </div>
  );
};
