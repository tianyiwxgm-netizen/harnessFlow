import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { patchConfigProfile } from '@/api/trim_profile';
import { apiClient } from '@/api/client';

describe('trim_profile api (PATCH /config/profile)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls PATCH /config/profile with profile body', async () => {
    const spy = vi
      .spyOn(apiClient, 'patch')
      .mockResolvedValue({ data: { profile: 'lean', synced: true } });
    const result = await patchConfigProfile('lean');
    expect(spy).toHaveBeenCalledWith('/config/profile', { profile: 'lean' });
    expect(result.profile).toBe('lean');
    expect(result.synced).toBe(true);
  });

  it('returns note when backend includes one', async () => {
    vi.spyOn(apiClient, 'patch').mockResolvedValue({
      data: { profile: 'custom', synced: true, note: 'custom checklist pending' },
    });
    const result = await patchConfigProfile('custom');
    expect(result.note).toBe('custom checklist pending');
  });

  it('rejects invalid profile synchronously', async () => {
    // @ts-expect-error — runtime guard test
    await expect(patchConfigProfile('bogus')).rejects.toThrow(/not a valid TrimProfile/);
  });

  it('propagates axios error', async () => {
    vi.spyOn(apiClient, 'patch').mockRejectedValue(new Error('network down'));
    await expect(patchConfigProfile('full')).rejects.toThrow(/network down/);
  });
});
