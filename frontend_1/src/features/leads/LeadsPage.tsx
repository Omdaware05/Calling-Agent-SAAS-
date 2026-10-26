import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/layout/PageHeader';
import { DataTable, Column } from '../../components/ui/DataTable';
import { Badge } from '../../components/ui/Badge';
import { StatusIndicator } from '../../components/ui/StatusIndicator';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Select } from '../../components/ui/Select';
import { CallDetailDrawer } from '../calls/CallDetailDrawer';
import { leadsApi } from '../../services/api/leads';
import { useToast } from '../../app/providers/ToastProvider';
import { useBusiness } from '../../app/providers/BusinessProvider';
import { getErrorMessage } from '../../services/api/client';
import { LeadDocument } from '../../types/api';
import { Target, Eye, RefreshCw, CheckCircle, Building2 } from 'lucide-react';
import { format } from 'date-fns';
import { TimeFilterAndExport } from '../../components/ui/TimeFilterAndExport';
import { exportToExcel, filterByDateRange, TimeFilterRange } from '../../utils/excelExport';

export const LeadsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { selectedBusiness, isAllBusinesses, getBusinessForAgent } = useBusiness();

  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
  const [editingLead, setEditingLead] = useState<LeadDocument | null>(null);
  const [leadStatus, setLeadStatus] = useState('new');
  const [leadNotes, setLeadNotes] = useState('');
  const [timeRange, setTimeRange] = useState<TimeFilterRange>('all');

  const { data: leads = [], isLoading, refetch } = useQuery({
    queryKey: ['leads'],
    queryFn: () => leadsApi.getLeads(),
    refetchInterval: 3000,
  });

  // Filter leads for selected business and date range
  const displayLeads = React.useMemo(() => {
    let result = leads;
    if (!isAllBusinesses && selectedBusiness) {
      const agentIds = new Set(selectedBusiness.assignedAgentIds);
      result = result.filter((l) => !l.agent_id || agentIds.has(l.agent_id));
    }
    return filterByDateRange(result, (l) => l.created_at, timeRange);
  }, [leads, selectedBusiness, isAllBusinesses, timeRange]);

  const handleExportExcel = () => {
    const exportRows = displayLeads.map((l) => ({
      'Lead ID': l.lead_id,
      'Prospect Phone': l.phone_number,
      'Pipeline Status': l.status || 'new',
      'Confidence Score': `${Math.round(((l.confidence_score !== undefined && l.confidence_score !== null) ? l.confidence_score : ((l as any).score ?? 0)) * 100)}%`,
      'Reasoning': l.reasoning || l.notes || 'N/A',
      'Call ID': l.call_id || 'N/A',
      'Agent ID': l.agent_id || 'N/A',
      'Captured At': l.created_at ? format(new Date(l.created_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A',
    }));
    exportToExcel(exportRows, `voxora_leads_pipeline_${timeRange}_${format(new Date(), 'yyyyMMdd')}`, 'Leads Pipeline');
  };

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { status?: string; notes?: string } }) =>
      leadsApi.updateLead(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead Updated', 'Status and notes recorded.');
      setEditingLead(null);
    },
    onError: (err) => {
      toast.error('Failed to update lead', getErrorMessage(err));
    },
  });

  const handleOpenEdit = (lead: LeadDocument) => {
    setEditingLead(lead);
    setLeadStatus(lead.status || 'new');
    setLeadNotes(lead.notes || '');
  };

  const handleSaveLead = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLead) return;
    updateMutation.mutate({
      id: editingLead.lead_id,
      payload: {
        status: leadStatus,
        notes: leadNotes,
      },
    });
  };

  const columns: Column<LeadDocument>[] = [
    {
      key: 'phone_number',
      header: 'Prospect Phone',
      sortable: true,
      render: (lead) => (
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center shrink-0 font-bold text-xs">
            <Target className="w-3.5 h-3.5" />
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">{lead.phone_number}</span>
            <span className="text-[10px] text-slate-400 font-mono">ID: {lead.lead_id}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'client_attribution',
      header: 'Client Business',
      render: (lead) => {
        const biz = getBusinessForAgent(lead.agent_id);
        return (
          <span className="text-xs text-slate-600 dark:text-zinc-400 truncate">
            {biz ? biz.name : selectedBusiness ? selectedBusiness.name : 'General Account'}
          </span>
        );
      },
    },
    {
      key: 'confidence_score',
      header: 'Interest Score',
      sortable: true,
      render: (lead) => {
        const rawScore = lead.confidence_score !== undefined && lead.confidence_score !== null ? lead.confidence_score : ((lead as any).score ?? 0);
        const pct = Math.round(rawScore * 100);
        return (
          <div className="w-24 space-y-1">
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">Confidence</span>
              <strong className="text-emerald-600 dark:text-emerald-400">{pct}%</strong>
            </div>
            <div className="w-full h-1 bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      },
    },
    {
      key: 'status',
      header: 'Pipeline Stage',
      sortable: true,
      render: (lead) => {
        const s = lead.status?.toLowerCase() || 'new';
        const type =
          s === 'converted'
            ? 'success'
            : s === 'qualified'
            ? 'active'
            : s === 'contacted'
            ? 'pending'
            : 'neutral';
        return <StatusIndicator status={type} label={lead.status || 'New'} />;
      },
    },
    {
      key: 'reasoning',
      header: 'Notes & AI Context',
      render: (lead) => (
        <p className="text-xs text-slate-600 dark:text-zinc-400 line-clamp-1 max-w-xs">
          {lead.reasoning || lead.notes || 'Identified via post-call intent classifier.'}
        </p>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (lead) => (
        <div className="flex items-center justify-end gap-1.5">
          <Button
            variant="outline"
            size="xs"
            onClick={() => handleOpenEdit(lead)}
          >
            Update
          </Button>
          {lead.call_id && (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => setSelectedCallId(lead.call_id)}
              leftIcon={<Eye className="w-3 h-3" />}
            >
              Call
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        category={isAllBusinesses ? 'CRM & Pipeline' : `Leads: ${selectedBusiness?.name}`}
        title="Interested Leads Pipeline"
        subtitle={
          isAllBusinesses
            ? 'Qualified prospective customers captured by AI voice telecallers across all client businesses.'
            : `Qualified prospective customer leads captured for ${selectedBusiness?.name}.`
        }
        actions={
          <div className="flex items-center gap-2.5 flex-wrap">
            <TimeFilterAndExport
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              onExport={handleExportExcel}
              filteredCount={displayLeads.length}
              label="Export Leads"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              leftIcon={<RefreshCw className="w-3.5 h-3.5 text-slate-400" />}
            >
              Refresh
            </Button>
          </div>
        }
      />

      <DataTable
        columns={columns}
        data={displayLeads}
        isLoading={isLoading}
        keyExtractor={(l) => l.lead_id}
        searchPlaceholder="Filter leads by phone or status..."
        searchableKey={(l) => `${l.phone_number} ${l.status || ''} ${l.reasoning || ''}`}
        emptyTitle="No leads captured yet"
        emptyDescription="Calls classified with high customer interest will automatically appear here."
        pageSize={10}
      />

      {/* Edit Lead Status Modal */}
      <Modal
        isOpen={!!editingLead}
        onClose={() => setEditingLead(null)}
        title={editingLead ? `Update Lead: ${editingLead.phone_number}` : 'Update Lead'}
        description="Modify the CRM lifecycle stage and attach follow-up operator notes."
        size="md"
      >
        <form onSubmit={handleSaveLead} className="space-y-4">
          <Select
            label="Pipeline Status"
            value={leadStatus}
            onChange={(e) => setLeadStatus(e.target.value)}
          >
            <option value="new">New Opportunity</option>
            <option value="contacted">Contacted</option>
            <option value="qualified">Sales Qualified</option>
            <option value="converted">Successfully Converted</option>
            <option value="closed">Closed / Disqualified</option>
          </Select>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
              Operator Notes
            </label>
            <textarea
              rows={3}
              value={leadNotes}
              onChange={(e) => setLeadNotes(e.target.value)}
              placeholder="Add follow-up notes, requested callback times, customer constraints..."
              className="w-full p-2.5 text-xs rounded-xl bg-white/70 dark:bg-white/[0.04] border border-slate-300/80 dark:border-white/[0.08] text-slate-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-orange-500/40"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 dark:border-white/[0.06]">
            <Button variant="ghost" size="sm" onClick={() => setEditingLead(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={updateMutation.isPending}
              leftIcon={<CheckCircle className="w-4 h-4" />}
            >
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      <CallDetailDrawer callId={selectedCallId} onClose={() => setSelectedCallId(null)} />
    </div>
  );
};
