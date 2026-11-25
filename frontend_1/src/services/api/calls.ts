import apiClient, { API_BASE_URL } from './client';
import { CallDocument, TranscriptDocument, InterestAnalysisDocument } from '../../types/api';

export const callsApi = {
  downloadAgentLeadExport: async (agentId: string, callIds: string[]): Promise<void> => {
    const res = await apiClient.get('/calls/export.xlsx', {
      params: { agent_id: agentId, call_ids: callIds.join(',') || undefined },
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'agent_lead_export.xlsx';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  getCalls: async (params?: {
    agent_id?: string;
    campaign_id?: string;
    state?: string;
    limit?: number;
    skip?: number;
  }): Promise<CallDocument[]> => {
    const res = await apiClient.get<any>('/calls', { params });
    if (Array.isArray(res.data)) return res.data;
    if (res.data && Array.isArray(res.data.calls)) return res.data.calls;
    return [];
  },

  getCall: async (callId: string): Promise<CallDocument> => {
    const res = await apiClient.get<CallDocument>(`/calls/${callId}`);
    return res.data;
  },

  hangupCall: async (callId: string): Promise<{ success: boolean; message?: string }> => {
    const res = await apiClient.post(`/calls/${callId}/hangup`);
    return res.data;
  },

  getTranscript: async (callId: string): Promise<TranscriptDocument> => {
    const res = await apiClient.get<TranscriptDocument>(`/calls/${callId}/transcript`);
    return res.data;
  },

  getRecordingUrl: (callId: string): string => {
    return `${API_BASE_URL}/calls/${callId}/recording`;
  },

  analyzeInterest: async (callId: string): Promise<InterestAnalysisDocument> => {
    const res = await apiClient.post<InterestAnalysisDocument>(`/calls/${callId}/analyze-interest`);
    return res.data;
  },

  getInterest: async (callId: string): Promise<InterestAnalysisDocument> => {
    const res = await apiClient.get<InterestAnalysisDocument>(`/calls/${callId}/interest`);
    return res.data;
  },
};
