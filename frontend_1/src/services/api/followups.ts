import apiClient from './client';
import { FollowupDocument, FollowupStatus } from '../../types/api';

export const followupsApi = {
  getFollowups: async (params?: { agent_id?: string; limit?: number; skip?: number }): Promise<FollowupDocument[]> => {
    const res = await apiClient.get<any>('/followups', { params });
    if (Array.isArray(res.data)) return res.data;
    if (res.data && Array.isArray(res.data.followups)) return res.data.followups;
    return [];
  },

  getFollowup: async (id: string): Promise<FollowupDocument> => {
    const res = await apiClient.get<FollowupDocument>(`/followups/${id}`);
    return res.data;
  },

  updateFollowup: async (
    id: string,
    payload: { status?: FollowupStatus; scheduled_at?: string; notes?: string }
  ): Promise<FollowupDocument> => {
    const res = await apiClient.patch<FollowupDocument>(`/followups/${id}`, payload);
    return res.data;
  },
};
