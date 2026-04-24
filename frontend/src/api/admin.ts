import { apiClient } from '@/api/client';

export interface AdminHealthResponse {
  status: 'ok' | 'degraded' | 'down';
  bff_version: string;
  uptime_seconds: number;
  services: Record<string, 'ok' | 'down' | 'unknown'>;
}

export async function fetchAdminHealth(): Promise<AdminHealthResponse> {
  const r = await apiClient.get<AdminHealthResponse>('/admin/health');
  return r.data;
}
