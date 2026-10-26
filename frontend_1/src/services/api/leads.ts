import apiClient from './client';
import { LeadDocument } from '../../types/api';

export const leadsApi = {
  getLeads: async (params?: { agent_id?: string; limit?: number; skip?: number }): Promise<LeadDocument[]> => {
    const res = await apiClient.get<any>('/leads', { params });
    if (Array.isArray(res.data)) return res.data;
    if (res.data && Array.isArray(res.data.leads)) return res.data.leads;
    return [];
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
