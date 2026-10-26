import apiClient from './client';
import { StatsResponse, ActiveCallsResponse, QueueResponse, ProviderBreakdownResponse } from '../../types/api';

export const statsApi = {
  getStats: async (): Promise<StatsResponse> => {
    const res = await apiClient.get<StatsResponse>('/stats');
    return res.data;
  },

  getActiveCalls: async (): Promise<ActiveCallsResponse> => {
    const res = await apiClient.get<ActiveCallsResponse>('/active-calls');
    return res.data;
  },

  getQueue: async (): Promise<QueueResponse> => {
    const res = await apiClient.get<QueueResponse>('/queue');
    return res.data;
  },

  getProviderBreakdown: async (): Promise<ProviderBreakdownResponse> => {
    const res = await apiClient.get<ProviderBreakdownResponse>('/stats/providers');
    return res.data;
  },
};
