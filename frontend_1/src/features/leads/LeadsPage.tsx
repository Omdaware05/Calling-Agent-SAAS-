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
import { Target, Eye, RefreshCw, CheckCircle, Building2, Download } from 'lucide-react';
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
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isDownloading, setIsDownloading] = useState(false);

  const { data: leads = [], isLoading, refetch } = useQuery({
    queryKey: ['leads'],
    queryFn: () => leadsApi.getLeads(),
    refetchInterval: 3000,
  });

  // Filter leads for selected business, pipeline status and date range
  const displayLeads = React.useMemo(() => {
    let result = leads;
    if (!isAllBusinesses && selectedBusiness) {
      const agentIds = new Set(selectedBusiness.assignedAgentIds);
      result = result.filter((l) => !l.agent_id || agentIds.has(l.agent_id));
    }
    if (statusFilter !== 'all') {
      result = result.filter((l) => (l.status || 'new').toLowerCase() === statusFilter);
    }
    return filterByDateRange(result, (l) => l.created_at, timeRange);
  }, [leads, selectedBusiness, isAllBusinesses, timeRange, statusFilter]);

  const handleExportExcel = () => {
    const exportRows = displayLeads.map((l) => {
      const ci = l.metadata?.customer_info || {};
      const reasonsText = (items?: { reason: string; evidence?: string }[]) =>
        (items || []).map((r) => `${r.reason} — "${r.evidence || ''}"`).join('; ');
      return {
        'Lead ID': l.lead_id,
        'Customer Name': l.name || ci.name || 'N/A',
        'Prospect Phone': l.phone_number,
        'Email': l.email || ci.email || 'N/A',
        'City': ci.city || 'N/A',
        'Budget (INR)': ci.budget_inr ?? 'N/A',
        'Pipeline Status': l.status || 'new',
        'Confidence Score': `${Math.round(((l.confidence_score !== undefined && l.confidence_score !== null) ? l.confidence_score : ((l as any).score ?? 0)) * 100)}%`,
        'Why Interested': reasonsText(l.metadata?.why_interested) || 'N/A',
        'Why Not Interested': reasonsText(l.metadata?.why_not_interested) || 'N/A',
        'Reasoning': l.reasoning || l.notes || 'N/A',
        'Call ID': l.call_id || 'N/A',
        'Agent ID': l.agent_id || 'N/A',
        'Captured At': l.created_at ? format(new Date(l.created_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A',
      };
    });
    exportToExcel(exportRows, `voxora_leads_pipeline_${statusFilter}_${timeRange}_${format(new Date(), 'yyyyMMdd')}`, 'Leads Pipeline');
  };

  // Server-side workbook (includes extracted customer info + why-reasons
  // for ALL matching leads, not just the rows loaded on this page).
  const handleDownloadServerExcel = async () => {
    setIsDownloading(true);
    try {
      await leadsApi.downloadLeadsExcel(statusFilter !== 'all' ? statusFilter : undefined);
      toast.success('Excel Downloaded', `Leads workbook (${statusFilter === 'all' ? 'all statuses' : statusFilter}) saved.`);
    } catch (err) {
      toast.error('Excel download failed', getErrorMessage(err));
    } finally {
      setIsDownloading(false);
    }
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
      key: 'customer',
      header: 'Customer (from call)',
      render: (lead) => {
        const ci = lead.metadata?.customer_info || {};
        const name = lead.name || ci.name;
        const email = lead.email || ci.email;
        const extras = [
          ci.city,
          ci.budget_inr ? `₹${ci.budget_inr.toLocaleString('en-IN')}` : null,
          ci.preferred_callback_time ? `↩ ${ci.preferred_callback_time}` : null,
        ].filter(Boolean).join(' · ');
        if (!name && !email && !extras) {
          return <span className="text-xs text-slate-400">Not stated on call</span>;
        }
        return (
          <div className="flex flex-col max-w-[190px]">
            {name && <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 truncate">{name}</span>}
            {email && <span className="text-[11px] text-slate-500 dark:text-zinc-400 truncate">{email}</span>}
            {extras && <span className="text-[11px] text-slate-500 dark:text-zinc-400 truncate">{extras}</span>}
          </div>
        );
      },
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
          s === 'interested' || s === 'qualified'
            ? 'success'
            : s === 'not_interested'
            ? 'danger'
            : s === 'closed'
            ? 'inactive'
            : 'pending';
        const label = s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        return <StatusIndicator status={type} label={label} />;
      },
    },
    {
      key: 'reasoning',
      header: 'Why — AI Reasons',
      render: (lead) => {
        const whyIn = lead.metadata?.why_interested || [];
        const whyNot = lead.metadata?.why_not_interested || [];
        const chip = (
          r: { reason: string; evidence?: string },
          cls: string,
        ) => (
          <span
            key={r.reason}
            title={r.evidence ? `Customer said: "${r.evidence}"` : undefined}
            className={`inline-block px-1.5 py-0.5 rounded-md text-[10px] font-medium leading-tight ${cls}`}
          >
            {r.reason}
          </span>
        );
        return (
          <div className="flex flex-col gap-1 max-w-[300px]">
            {(whyIn.length > 0 || whyNot.length > 0) && (
              <div className="flex flex-wrap gap-1">
                {whyIn.map((r) => chip(r, 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'))}
                {whyNot.map((r) => chip(r, 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300'))}
              </div>
            )}
            <p className="text-xs text-slate-600 dark:text-zinc-400 line-clamp-2">
              {lead.reasoning || lead.notes || 'No reason recorded for this lead yet.'}
            </p>
          </div>
        );
      },
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
        title="Leads Pipeline"
        subtitle={
          isAllBusinesses
            ? 'Every lead captured by AI voice telecallers — with the customer details and the reason (interested or not) extracted from each call.'
            : `Customer leads captured for ${selectedBusiness?.name}, with call-extracted details and AI reasons.`
        }
        actions={
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="w-44">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter leads by status"
              >
                <option value="all">All Statuses</option>
                <option value="interested">Interested</option>
                <option value="not_interested">Not Interested</option>
                <option value="new">New</option>
                <option value="qualified">Qualified</option>
                <option value="closed">Closed</option>
              </Select>
            </div>
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
              onClick={handleDownloadServerExcel}
              isLoading={isDownloading}
              leftIcon={<Download className="w-3.5 h-3.5 text-slate-400" />}
            >
              Excel (Server)
            </Button>
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
        searchPlaceholder="Filter leads by phone, name, email or status..."
        searchableKey={(l) => `${l.phone_number} ${l.status || ''} ${l.reasoning || ''} ${l.name || ''} ${l.email || ''} ${l.metadata?.customer_info?.city || ''}`}
        emptyTitle="No leads captured yet"
        emptyDescription="Analyzed calls will automatically appear here as leads, with their extracted customer details and reasons."
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
            <option value="interested">Interested</option>
            <option value="not_interested">Not Interested</option>
            <option value="qualified">Sales Qualified</option>
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
