import { describe, it, expect, beforeEach } from 'vitest';
import { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios';
import { apiClient, PID_HEADER } from '@/api/client';
import { setActivePid, clearActivePid } from '@/utils/pid';

describe('apiClient', () => {
  beforeEach(() => {
    clearActivePid();
  });

  it('has /api as baseURL', () => {
    expect(apiClient.defaults.baseURL).toBe('/api');
  });

  it('omits pid header when no active pid', async () => {
    const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig;
    // @ts-expect-error private API — interceptor[0] is our injector
    const handler = apiClient.interceptors.request.handlers[0].fulfilled;
    const result: InternalAxiosRequestConfig = await handler(config);
    expect(result.headers.get(PID_HEADER)).toBeFalsy();
  });

  it('adds X-Harness-Pid header via interceptor when pid is active', async () => {
    setActivePid('pj-xyz');
    const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig;
    // @ts-expect-error private API — interceptor[0] is our injector
    const handler = apiClient.interceptors.request.handlers[0].fulfilled;
    const result: InternalAxiosRequestConfig = await handler(config);
    expect(result.headers.get(PID_HEADER)).toBe('pj-xyz');
  });
});
