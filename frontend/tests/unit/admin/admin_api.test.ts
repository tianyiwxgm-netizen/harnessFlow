import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchAdminHealth } from '@/api/admin';
import { apiClient } from '@/api/client';

describe('admin api · /admin/health', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('GET /admin/health happy path', async () => {
    const spy = vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { status: 'ok', bff_version: '0.1.0', uptime_seconds: 1, services: { bff: 'ok' } },
    });
    const res = await fetchAdminHealth();
    expect(spy).toHaveBeenCalledWith('/admin/health');
    expect(res.status).toBe('ok');
    expect(res.services.bff).toBe('ok');
  });

  it('propagates error to caller', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('boom'));
    await expect(fetchAdminHealth()).rejects.toThrow(/boom/);
  });
});
