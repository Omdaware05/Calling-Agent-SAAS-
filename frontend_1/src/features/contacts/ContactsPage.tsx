import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/layout/PageHeader';
import { DataTable, Column } from '../../components/ui/DataTable';
import { InterestBadge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { CsvImportModal } from './CsvImportModal';
import { contactsApi } from '../../services/api/contacts';
import { useToast } from '../../app/providers/ToastProvider';
import { useBusiness } from '../../app/providers/BusinessProvider';
import { getErrorMessage } from '../../services/api/client';
import { ContactDocument } from '../../types/api';
import { Users, Plus, UploadCloud, RefreshCw, PhoneCall } from 'lucide-react';
import { format } from 'date-fns';

export const ContactsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { selectedBusiness, isAllBusinesses } = useBusiness();

  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // New Contact form
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const { data: contacts = [], isLoading, refetch } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => contactsApi.getContacts({ limit: 100 }),
  });

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

  const columns: Column<ContactDocument>[] = [
    {
      key: 'phone_number',
      header: 'Contact Details',
      sortable: true,
      render: (c) => (
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center shrink-0 font-bold text-xs">
            {c.name ? c.name.charAt(0).toUpperCase() : <PhoneCall className="w-3.5 h-3.5" />}
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">{c.name || 'Unnamed Contact'}</span>
            <span className="text-[11px] text-slate-500 font-mono">{c.phone_number}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'email',
      header: 'Email',
      render: (c) => <span className="text-xs text-slate-500">{c.email || '—'}</span>,
    },
    {
      key: 'interaction_count',
      header: 'Call Turns',
      sortable: true,
      align: 'center',
      render: (c) => (
        <span className="font-mono text-xs font-semibold text-slate-700 dark:text-zinc-300 tabular-nums">
          {c.interaction_count}
        </span>
      ),
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
            <span className="text-xs text-slate-500 font-mono">
              {format(new Date(c.created_at), 'MMM dd, yyyy')}
            </span>
          );
        } catch {
          return <span className="text-xs text-slate-500 font-mono">{c.created_at}</span>;
        }
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        category={isAllBusinesses ? 'CRM & Database' : `Contacts: ${selectedBusiness?.name}`}
        title="Contact Intelligence & Directory"
        subtitle={
          isAllBusinesses
            ? 'Manage customer profiles, interaction memory, and CSV data synchronization.'
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

      <DataTable
        columns={columns}
        data={contacts}
        isLoading={isLoading}
        keyExtractor={(c) => c.contact_id}
        searchPlaceholder="Filter contacts by phone or name..."
        searchableKey={(c) => `${c.phone_number} ${c.name || ''} ${c.email || ''}`}
        emptyTitle="No contacts in database"
        emptyDescription="Add contacts manually or import from a CSV spreadsheet."
        pageSize={12}
      />

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
    </div>
  );
};
