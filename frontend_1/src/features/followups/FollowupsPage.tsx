import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/layout/PageHeader';
import { DataTable, Column } from '../../components/ui/DataTable';
import { StatusIndicator } from '../../components/ui/StatusIndicator';
import { Button } from '../../components/ui/Button';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { followupsApi } from '../../services/api/followups';
import { useToast } from '../../app/providers/ToastProvider';
import { useBusiness } from '../../app/providers/BusinessProvider';
import { getErrorMessage } from '../../services/api/client';
import { FollowupDocument, FollowupStatus } from '../../types/api';
import { CalendarClock, RefreshCw, CheckCircle } from 'lucide-react';
import { format } from 'date-fns';
import { TimeFilterAndExport } from '../../components/ui/TimeFilterAndExport';
import { exportToExcel, filterByDateRange, TimeFilterRange } from '../../utils/excelExport';

export const FollowupsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { selectedBusiness, isAllBusinesses } = useBusiness();

  const [editingFollowup, setEditingFollowup] = useState<FollowupDocument | null>(null);
  const [status, setStatus] = useState<FollowupStatus>('scheduled');
  const [scheduledAt, setScheduledAt] = useState('');
  const [notes, setNotes] = useState('');
  const [timeRange, setTimeRange] = useState<TimeFilterRange>('all');

  const { data: followups = [], isLoading, refetch } = useQuery({
    queryKey: ['followups'],
    queryFn: () => followupsApi.getFollowups(),
    refetchInterval: 3000,
  });

  const displayFollowups = React.useMemo(() => {
    return filterByDateRange(followups, (f) => f.scheduled_at || f.created_at, timeRange);
  }, [followups, timeRange]);

  const handleExportExcel = () => {
    const exportRows = displayFollowups.map((f) => ({
      'Follow-up ID': f.followup_id,
      'Contact Phone Number': f.phone_number,
      'Status': f.status,
      'Scheduled Callback Time': f.scheduled_at ? format(new Date(f.scheduled_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A',
      'Detected Reason & Action': f.notes || 'N/A',
      'Associated Call ID': f.call_id || 'N/A',
      'Created At': f.created_at ? format(new Date(f.created_at), 'yyyy-MM-dd HH:mm:ss') : 'N/A',
    }));
    exportToExcel(exportRows, `voxora_followups_${timeRange}_${format(new Date(), 'yyyyMMdd')}`, 'Follow-ups');
  };

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: { status?: FollowupStatus; scheduled_at?: string; notes?: string };
    }) => followupsApi.updateFollowup(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['followups'] });
      toast.success('Follow-up Updated');
      setEditingFollowup(null);
    },
    onError: (err) => {
      toast.error('Failed to update follow-up', getErrorMessage(err));
    },
  });

  const handleOpenEdit = (f: FollowupDocument) => {
    setEditingFollowup(f);
    setStatus(f.status || 'scheduled');
    setNotes(f.notes || '');
    try {
      setScheduledAt(new Date(f.scheduled_at).toISOString().slice(0, 16));
    } catch {
      setScheduledAt('');
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingFollowup) return;
    updateMutation.mutate({
      id: editingFollowup.followup_id,
      payload: {
        status,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
        notes,
      },
    });
  };

  const columns: Column<FollowupDocument>[] = [
    {
      key: 'phone_number',
      header: 'Contact Phone Number',
      sortable: true,
      render: (f) => (
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-300 flex items-center justify-center shrink-0 font-bold text-xs">
            <CalendarClock className="w-3.5 h-3.5" />
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">{f.phone_number}</span>
            <span className="text-[10px] text-slate-400 font-mono">ID: {f.followup_id}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'scheduled_at',
      header: 'Scheduled Callback Time',
      sortable: true,
      render: (f) => {
        try {
          return (
            <span className="text-xs font-mono font-medium text-slate-700 dark:text-zinc-300">
              {format(new Date(f.scheduled_at), 'MMM dd, yyyy · HH:mm')}
            </span>
          );
        } catch {
          return <span className="text-xs font-mono text-slate-500">{f.scheduled_at}</span>;
        }
      },
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (f) => {
        const type =
          f.status === 'completed'
            ? 'success'
            : f.status === 'scheduled'
            ? 'active'
            : f.status === 'cancelled'
            ? 'danger'
            : 'pending';
        return <StatusIndicator status={type} label={f.status} />;
      },
    },
    {
      key: 'notes',
      header: 'Detected Reason & Follow-up Action',
      render: (f) => {
        if (!f.notes) return <span className="text-xs text-slate-400">—</span>;
        const notesLower = f.notes.toLowerCase();
        const isBusy = f.notes.includes('PHONE / LINE BUSY') || f.notes.includes('Category 2') || notesLower.includes('busy');
        const isNotAnswered = f.notes.includes('CALL NOT ANSWERED') || f.notes.includes('Category 3') || notesLower.includes('no_answer') || notesLower.includes('not answered');
        return (
          <div className="flex flex-col gap-1 max-w-md">
            <div className="flex items-center gap-1.5 flex-wrap">
              {isBusy && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-400 border border-amber-200/50 dark:border-amber-800/40 shrink-0">
                  ⚠️ Line Busy
                </span>
              )}
              {isNotAnswered && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-white/10 text-slate-700 dark:text-zinc-300 border border-slate-200/50 dark:border-white/10 shrink-0">
                  📵 Not Answered
                </span>
              )}
              <span className="text-xs text-slate-700 dark:text-zinc-300 font-medium">
                {f.notes}
              </span>
            </div>
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (f) => (
        <Button variant="outline" size="xs" onClick={() => handleOpenEdit(f)}>
          Manage
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        category={isAllBusinesses ? 'CRM & Outreach' : `Follow-ups: ${selectedBusiness?.name}`}
        title="Scheduled Callbacks & Follow-ups"
        subtitle={
          isAllBusinesses
            ? 'Track customer callbacks requested during conversations across all client accounts.'
            : `Scheduled customer callbacks for ${selectedBusiness?.name}.`
        }
        actions={
          <div className="flex items-center gap-2.5 flex-wrap">
            <TimeFilterAndExport
              timeRange={timeRange}
              onTimeRangeChange={setTimeRange}
              onExport={handleExportExcel}
              filteredCount={displayFollowups.length}
              label="Export Follow-ups"
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
        data={displayFollowups}
        isLoading={isLoading}
        keyExtractor={(f) => f.followup_id}
        searchPlaceholder="Filter follow-ups by phone, notes..."
        searchableKey={(f) => `${f.phone_number} ${f.status} ${f.notes || ''}`}
        emptyTitle="No scheduled follow-ups"
        emptyDescription="Any callback request scheduled during a voice turn will appear here."
        pageSize={10}
      />

      {/* Edit Modal */}
      <Modal
        isOpen={!!editingFollowup}
        onClose={() => setEditingFollowup(null)}
        title="Manage Follow-up Callback"
        description="Update scheduled time, mark as completed, or attach operator notes."
        size="md"
      >
        <form onSubmit={handleSave} className="space-y-4">
          <Input
            label="Scheduled Date & Time"
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            required
          />

          <Select
            label="Follow-up Status"
            value={status}
            onChange={(e) => setStatus(e.target.value as FollowupStatus)}
          >
            <option value="scheduled">Scheduled</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </Select>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
              Notes
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add reminder details..."
              className="w-full p-2.5 text-xs rounded-xl bg-white/70 dark:bg-white/[0.04] border border-slate-300/80 dark:border-white/[0.08] text-slate-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-orange-500/40"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 dark:border-white/[0.06]">
            <Button variant="ghost" size="sm" onClick={() => setEditingFollowup(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={updateMutation.isPending}
              leftIcon={<CheckCircle className="w-4 h-4" />}
            >
              Update Callback
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
