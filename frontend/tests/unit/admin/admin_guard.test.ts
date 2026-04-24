import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import { useUISessionStore } from '@/stores/ui_session';

function makeRouter() {
  const router = createRouter({ history: createMemoryHistory(), routes });
  installGuards(router);
  return router;
}

describe('router admin guard (L2-07 requiresAdmin meta)', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('admin=true allows /tabs/admin_entry', async () => {
    const router = makeRouter();
    const store = useUISessionStore();
    store.setAdmin(true);
    await router.push('/tabs/admin_entry/health');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/admin_entry/health');
  });

  it('admin=false blocks /tabs/admin_entry and redirects to overview', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const router = makeRouter();
    const store = useUISessionStore();
    store.setAdmin(false);
    await router.push('/tabs/admin_entry/users');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/overview');
    warn.mockRestore();
  });

  it('admin=false still allows non-admin tabs', async () => {
    const router = makeRouter();
    const store = useUISessionStore();
    store.setAdmin(false);
    await router.push('/tabs/kb');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/kb');
  });

  it('/tabs/admin_entry without subtab redirects to /health', async () => {
    const router = makeRouter();
    await router.push('/tabs/admin_entry');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/admin_entry/health');
  });

  it('/tabs/admin_entry/<unknown> redirects to /health', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const router = makeRouter();
    await router.push('/tabs/admin_entry/bogus_sub');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/admin_entry/health');
    warn.mockRestore();
  });

  it('each of 8 admin subtabs resolves to its path', async () => {
    const router = makeRouter();
    for (const sid of [
      'users',
      'permissions',
      'audit',
      'backup',
      'config',
      'health',
      'metrics',
      'red_line_alerts',
    ] as const) {
      await router.push(`/tabs/admin_entry/${sid}`);
      await router.isReady();
      expect(router.currentRoute.value.path).toBe(`/tabs/admin_entry/${sid}`);
      expect(router.currentRoute.value.meta.adminSubtabId).toBe(sid);
    }
  });

  it('admin subtab routes carry meta.requiresAdmin=true', async () => {
    const router = makeRouter();
    await router.push('/tabs/admin_entry/audit');
    await router.isReady();
    const hasAdminMeta = router.currentRoute.value.matched.some(
      (r) => r.meta?.requiresAdmin === true,
    );
    expect(hasAdminMeta).toBe(true);
  });
});
