import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/layout/PageHeader';
import { DataTable, Column } from '../../components/ui/DataTable';
import { InterestBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { MetricCard } from '../../components/ui/MetricCard';
import { CallDetailDrawer } from '../calls/CallDetailDrawer';
import { CsvImportModal } from './CsvImportModal';
import { contactsApi } from '../../services/api/contacts';
import { agentsApi } from '../../services/api/agents';
import { useToast } from '../../app/providers/ToastProvider';
import { useBusiness } from '../../app/providers/BusinessProvider';
import { getErrorMessage } from '../../services/api/client';
import { ContactDocument } from '../../types/api';
import {
  Users,
  Plus,
  UploadCloud,
  RefreshCw,
  PhoneCall,
  Phone,
  Eye,
  CheckCircle,
  ThumbsDown,
  Clock,
  Sparkles,
} from 'lucide-react';
import { format } from 'date-fns';
import { formatDateTime } from '../../utils/dateUtils';

export const ContactsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { selectedBusiness, isAllBusinesses } = useBusiness();

  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);

  // Quick Dial Modal
  const [dialContact, setDialContact] = useState<ContactDocument | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [isDialing, setIsDialing] = useState(false);

  // New Contact form
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const { data: contacts = [], isLoading, refetch } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => contactsApi.getContacts({ limit: 200 }),
    refetchInterval: 5000,
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.getAgents(),
  });

  // Default agent selector
  const defaultAgentId = useMemo(() => {
    if (selectedAgentId) return selectedAgentId;
    if (agents.length > 0) return agents[0].agent_id;
    return 'agent-admission-advisor';
  }, [agents, selectedAgentId]);

  // Summary Metrics
  const totalContacts = contacts.length;
  const contactedCount = contacts.filter((c) => (c.interaction_count || 0) > 0).length;
  const interestedCount = contacts.filter(
    (c) =>
      c.last_interest_status &&
      ['interested', 'callback_requested', 'qualified', 'hot'].includes(c.last_interest_status.toLowerCase())
  ).length;
  const notInterestedCount = contacts.filter(
    (c) =>
      c.last_interest_status &&
      ['not_interested', 'rejected', 'opt_out', 'disqualified'].includes(c.last_interest_status.toLowerCase())
  ).length;

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) {
      toast.error('Phone number is required');
      return;
    }

    setIsCreating(true);
    try {
      await contactsApi.createOrUpdateContact({
        phone_number: phone.trim(),
        name: name.trim() || undefined,
        email: email.trim() || undefined,
      });
      toast.success('Contact Saved', `${phone} added to CRM.`);
      setIsAddModalOpen(false);
      setPhone('');
      setName('');
      setEmail('');
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    } catch (err: any) {
      toast.error('Failed to add contact', getErrorMessage(err));
    } finally {
      setIsCreating(false);
    }
  };

  const handleTriggerCall = async () => {
    if (!dialContact) return;
    const targetAgent = selectedAgentId || defaultAgentId;
    if (!targetAgent) {
      toast.error('No Voice Agent available', 'Please configure an agent first.');
      return;
    }

    setIsDialing(true);
    try {
      await agentsApi.startCalls(targetAgent, {
        phone_numbers: [dialContact.phone_number],
      });
      toast.success('Call Dispatched', `Calling ${dialContact.phone_number} with AI Agent.`);
      setDialContact(null);
      setTimeout(() => {
        refetch();
        queryClient.invalidateQueries({ queryKey: ['calls'] });
      }, 1500);
    } catch (err: any) {
      toast.error('Call Dispatch Failed', getErrorMessage(err));
    } finally {
      setIsDialing(false);
    }
  };

  const columns: Column<ContactDocument>[] = [
    {
      key: 'phone_number',
      header: 'Contact Details',
      sortable: true,
      render: (c) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20 flex items-center justify-center shrink-0 font-bold text-xs shadow-sm">
            {c.name ? c.name.charAt(0).toUpperCase() : <Phone className="w-3.5 h-3.5" />}
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              {c.name || 'Prospect'}
            </span>
            <span className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono tracking-wide">
              {c.phone_number}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'email',
      header: 'Email Address',
      render: (c) => (
        <span className="text-xs text-slate-500 dark:text-zinc-400">
          {c.email || <span className="text-slate-400 italic">Not provided</span>}
        </span>
      ),
    },
    {
      key: 'interaction_count',
      header: 'Total Calls',
      sortable: true,
      align: 'center',
      render: (c) => {
        const count = c.interaction_count || 0;
        return (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono font-semibold ${
              count > 0
                ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20'
                : 'bg-slate-100 dark:bg-white/[0.04] text-slate-400'
            }`}
          >
            {count} {count === 1 ? 'call' : 'calls'}
          </span>
        );
      },
    },
    {
      key: 'last_interest_status',
      header: 'Last Interest',
      render: (c) => <InterestBadge status={c.last_interest_status} size="xs" />,
    },
    {
      key: 'created_at',
      header: 'Registered',
      sortable: true,
      render: (c) => {
        try {
          return (
            <span className="text-xs text-slate-500 dark:text-zinc-400 font-mono">
              {formatDateTime(c.created_at, 'MMM dd, yyyy · hh:mm a')}
            </span>
          );
        } catch {
          return <span className="text-xs text-slate-500 font-mono">{c.created_at}</span>;
        }
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (c) => (
        <div className="flex items-center justify-end gap-1.5">
          <Button
            variant="outline"
            size="xs"
            onClick={() => {
              setDialContact(c);
              setSelectedAgentId(defaultAgentId);
            }}
            leftIcon={<PhoneCall className="w-3 h-3 text-orange-500" />}
            className="hover:border-orange-500/40 hover:text-orange-500"
          >
            Call
          </Button>
          {c.last_call_id && (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => setSelectedCallId(c.last_call_id!)}
              leftIcon={<Eye className="w-3 h-3 text-slate-400" />}
              className="hover:bg-slate-100 dark:hover:bg-white/[0.06]"
              title="Inspect latest call audio and transcript"
            >
              Telemetry
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        category={isAllBusinesses ? 'CRM & Database' : `Contacts: ${selectedBusiness?.name}`}
        title="Contact Intelligence & Directory"
        subtitle={
          isAllBusinesses
            ? 'Manage customer profiles, interaction memory, call triggers, and CSV synchronization.'
            : `Client contact records for ${selectedBusiness?.name}.`
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              leftIcon={<RefreshCw className="w-3.5 h-3.5 text-slate-400" />}
            >
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCsvModalOpen(true)}
              leftIcon={<UploadCloud className="w-4 h-4 text-slate-400" />}
            >
              Import CSV
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsAddModalOpen(true)}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Add Contact
            </Button>
          </div>
        }
      />

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Contacts"
          value={totalContacts}
          subtext="Registered directory profiles"
          icon={<Users className="w-5 h-5 text-orange-500" />}
          isLoading={isLoading}
        />
        <MetricCard
          label="Engaged / Called"
          value={contactedCount}
          subtext={`${totalContacts > 0 ? Math.round((contactedCount / totalContacts) * 100) : 0}% outreach coverage`}
          icon={<Phone className="w-5 h-5 text-blue-500" />}
          isLoading={isLoading}
        />
        <MetricCard
          label="Interested Prospects"
          value={interestedCount}
          subtext="Confirmed lead intent"
          icon={<CheckCircle className="w-5 h-5 text-emerald-500" />}
          glow={interestedCount > 0}
          isLoading={isLoading}
        />
        <MetricCard
          label="Not Interested"
          value={notInterestedCount}
          subtext="Declined or opt-out list"
          icon={<ThumbsDown className="w-5 h-5 text-rose-500" />}
          isLoading={isLoading}
        />
      </div>

      <div className="rounded-2xl border border-slate-200/80 dark:border-white/[0.06] bg-white/50 dark:bg-zinc-900/50 backdrop-blur-sm overflow-hidden shadow-sm">
        <DataTable
          columns={columns}
          data={contacts}
          isLoading={isLoading}
          keyExtractor={(c) => c.contact_id}
          searchPlaceholder="Filter contacts by phone, name, email or status..."
          searchableKey={(c) => `${c.phone_number} ${c.name || ''} ${c.email || ''} ${c.last_interest_status || ''}`}
          emptyTitle="No contacts in database"
          emptyDescription="Add contacts manually or import from a CSV spreadsheet."
          pageSize={12}
        />
      </div>

      <CsvImportModal
        isOpen={isCsvModalOpen}
        onClose={() => setIsCsvModalOpen(false)}
        onSuccess={() => refetch()}
      />

      {/* Manual Add Contact Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add Single Contact"
        description="Register a phone number and customer profile into CRM database."
        size="md"
      >
        <form onSubmit={handleAddContact} className="space-y-4">
          <Input
            label="Phone Number"
            placeholder="+919876543210"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            helperText="Include country code (e.g. +91)"
          />
          <Input
            label="Contact Full Name"
            placeholder="e.g. Ramesh Kumar"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            label="Email Address"
            type="email"
            placeholder="ramesh@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 dark:border-zinc-800">
            <Button variant="ghost" size="sm" onClick={() => setIsAddModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isCreating}>
              Save Contact
            </Button>
          </div>
        </form>
      </Modal>

      {/* Quick Outbound Dial Confirmation Modal */}
      <Modal
        isOpen={!!dialContact}
        onClose={() => setDialContact(null)}
        title={dialContact ? `Call ${dialContact.phone_number}` : 'Initiate Call'}
        description="Select the AI Voice Agent to dial this contact immediately."
        size="md"
      >
        <div className="space-y-4 py-2">
          <div className="p-3 rounded-xl bg-slate-100 dark:bg-white/[0.04] border border-slate-200/80 dark:border-white/[0.08] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Phone className="w-4 h-4 text-orange-500" />
              <span className="font-semibold text-xs text-slate-900 dark:text-white font-mono">
                {dialContact?.phone_number}
              </span>
            </div>
            {dialContact?.name && (
              <span className="text-xs text-slate-500 font-medium">{dialContact.name}</span>
            )}
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
              Select Calling Agent
            </label>
            <Select
              value={selectedAgentId || defaultAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
            >
              {agents.map((ag) => (
                <option key={ag.agent_id} value={ag.agent_id}>
                  {ag.name} ({ag.language_mode || 'Hindi/English'})
                </option>
              ))}
            </Select>
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 dark:border-white/[0.06]">
            <Button variant="ghost" size="sm" onClick={() => setDialContact(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleTriggerCall}
              isLoading={isDialing}
              leftIcon={<PhoneCall className="w-4 h-4" />}
            >
              Start Call Now
            </Button>
          </div>
        </div>
      </Modal>

      {/* Call Telemetry Drawer */}
      <CallDetailDrawer callId={selectedCallId} onClose={() => setSelectedCallId(null)} />
    </div>
  );
};
