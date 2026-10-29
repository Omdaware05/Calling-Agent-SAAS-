import apiClient from './client';
import { LeadDocument } from '../../types/api';

export const leadsApi = {
  getLeads: async (params?: { agent_id?: string; limit?: number; skip?: number }): Promise<LeadDocument[]> => {
    // Default to the backend maximum page size so leads beyond the old
    // default of 50 are not silently invisible (and missing from exports).
    const res = await apiClient.get<any>('/leads', { params: { limit: 500, ...params } });
    if (Array.isArray(res.data)) return res.data;
    if (res.data && Array.isArray(res.data.leads)) return res.data.leads;
    return [];
  },

  /**
   * Download the server-generated Excel workbook of leads
   * (GET /leads/export.xlsx), optionally filtered by status,
   * e.g. 'interested' or 'not_interested'.
   */
  downloadLeadsExcel: async (status?: string): Promise<void> => {
    const res = await apiClient.get('/leads/export.xlsx', {
      params: status ? { status } : {},
      responseType: 'blob',
    });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leads_${status || 'all'}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Delay revoking: an immediate revoke can cancel the download in
    // some browsers (observed as a 0-byte file in Firefox).
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  },

  getLead: async (id: string): Promise<LeadDocument> => {
    const res = await apiClient.get<LeadDocument>(`/leads/${id}`);
    return res.data;
  },

  updateLead: async (id: string, payload: { status?: string; notes?: string }): Promise<LeadDocument> => {
    const res = await apiClient.patch<LeadDocument>(`/leads/${id}`, payload);
    return res.data;
  },
};
