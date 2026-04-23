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

describe('router guards (L2-01 路由守则)', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('root path "/" redirects to /tabs/overview by default', async () => {
    const router = makeRouter();
    await router.push('/');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/overview');
  });

  it('root path redirects to last stored tab', async () => {
    localStorage.setItem('harnessflow.active_tab', 'wbs');
    const router = makeRouter();
    await router.push('/');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/wbs');
  });

  it('/tabs/<valid> resolves and updates store activeTabId', async () => {
    const router = makeRouter();
    await router.push('/tabs/gate');
    await router.isReady();
    const store = useUISessionStore();
    expect(router.currentRoute.value.path).toBe('/tabs/gate');
    expect(store.activeTabId).toBe('gate');
  });

  it('/tabs/<unknown> redirects to /tabs/<lastTab> via catch-all', async () => {
    const router = makeRouter();
    await router.push('/tabs/definitely_fake');
    await router.isReady();
    // Unknown child falls through the catch-all → "/" → /tabs/<lastTab>
    expect(router.currentRoute.value.path).toBe('/tabs/overview');
  });

  it('totally unknown path (/:pathMatch) redirects to /', async () => {
    const router = makeRouter();
    await router.push('/some/bogus/path');
    await router.isReady();
    // catch-all redirects to /, which redirects to /tabs/overview
    expect(router.currentRoute.value.path).toBe('/tabs/overview');
  });

  it('?pid=<x> on first access adopts pid as active project', async () => {
    const router = makeRouter();
    await router.push('/tabs/overview?pid=pj-first');
    await router.isReady();
    const store = useUISessionStore();
    expect(store.activeProjectId).toBe('pj-first');
  });

  it('?pid=<same> with matching active project is allowed', async () => {
    const router = makeRouter();
    await router.push('/tabs/overview?pid=pj-a');
    await router.isReady();
    await router.push('/tabs/wbs?pid=pj-a');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/tabs/wbs');
    const store = useUISessionStore();
    expect(store.activeProjectId).toBe('pj-a');
  });

  it('?pid=<other> when active project is different is blocked (PM-14)', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const router = makeRouter();
    await router.push('/tabs/overview?pid=pj-a');
    await router.isReady();
    await router.push('/tabs/wbs?pid=pj-b');
    await router.isReady();
    // blocked — stays on overview (last valid tab)
    expect(router.currentRoute.value.path).toBe('/tabs/overview');
    const warnCalls = warn.mock.calls.flat().join(' ');
    expect(warnCalls).toContain('cross_project_access_denied');
    warn.mockRestore();
  });

  it('blocked cross-pid navigation preserves active project id', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const router = makeRouter();
    await router.push('/tabs/overview?pid=pj-a');
    await router.isReady();
    await router.push('/tabs/wbs?pid=pj-b');
    await router.isReady();
    const store = useUISessionStore();
    expect(store.activeProjectId).toBe('pj-a');
    warn.mockRestore();
  });

  it('each of the 11 canonical tabs resolves successfully', async () => {
    const router = makeRouter();
    for (const id of [
      'overview',
      'gate',
      'artifacts',
      'progress',
      'wbs',
      'decision_flow',
      'quality',
      'kb',
      'retro',
      'events',
      'admin_entry',
    ] as const) {
      await router.push(`/tabs/${id}`);
      await router.isReady();
      expect(router.currentRoute.value.path).toBe(`/tabs/${id}`);
      expect(router.currentRoute.value.meta.tabId).toBe(id);
    }
  });

  it('route meta includes title from TAB_REGISTRY', async () => {
    const router = makeRouter();
    await router.push('/tabs/kb');
    await router.isReady();
    expect(router.currentRoute.value.meta.title).toBe('知识库');
  });
});
