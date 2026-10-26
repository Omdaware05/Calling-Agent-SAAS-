import axios, { AxiosError } from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000,
});

// Request interceptor for token injection
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('api_auth_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
    config.headers['X-API-Token'] = token;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string | Array<{ loc?: string[]; msg?: string }> }>) => {
    if (error.response) {
      if (error.response.status === 401) {
        // Dispatched via custom event for UI reaction without hard page reload
        window.dispatchEvent(new CustomEvent('voxora:auth_required'));
      }
    }
    return Promise.reject(error);
  }
);

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data: any = error.response?.data;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data?.message === 'string') return data.message;
    if (data?.detail && typeof data.detail === 'object') {
      if (typeof data.detail.message === 'string') return data.detail.message;
      if (typeof data.detail.detail === 'string') return data.detail.detail;
    }
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      return data.detail.map((d: any) => d.msg || 'Validation error').join(', ');
    }
    return error.message || 'An unexpected server error occurred';
  }
  if (error instanceof Error) return error.message;
  return 'An unknown error occurred';
}

export default apiClient;
