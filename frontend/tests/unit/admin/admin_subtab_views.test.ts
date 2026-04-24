import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import App from '@/App.vue';
import { useUISessionStore } from '@/stores/ui_session';
import { ADMIN_SUBTAB_IDS, ADMIN_SUBTAB_REGISTRY } from '@/domain/admin_subtabs';
import * as adminApi from '@/api/admin';

async function mountApp(path: string) {
  setActivePinia(createPinia());
  const store = useUISessionStore();
  store.setAdmin(true);
  const router = createRouter({ history: createMemoryHistory(), routes });
  installGuards(router);
  await router.push(path);
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  await flushPromises();
  return { wrapper, router };
}

describe('admin subtab placeholder views', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  // 7 静态 placeholder — parameterised
  const staticSubtabs = ADMIN_SUBTAB_IDS.filter((s) => s !== 'health');
  for (const sid of staticSubtabs) {
    it(`${sid} view renders title + placeholder hint`, async () => {
      const { wrapper } = await mountApp(`/tabs/admin_entry/${sid}`);
      const view = wrapper.find(`[data-test="admin-subtab-view-${sid}"]`);
      expect(view.exists()).toBe(true);
      expect(view.find('h4').text()).toBe(ADMIN_SUBTAB_REGISTRY[sid].title);
    });
  }

  it('health view shows loading then data on success', async () => {
    vi.spyOn(adminApi, 'fetchAdminHealth').mockResolvedValue({
      status: 'ok',
      bff_version: '0.1.0',
      uptime_seconds: 1.23,
      services: { bff: 'ok' },
    });
    const { wrapper } = await mountApp('/tabs/admin_entry/health');
    // wait an extra tick in case of onMounted timing
    await flushPromises();
    const view = wrapper.find('[data-test="admin-subtab-view-health"]');
    expect(view.exists()).toBe(true);
    expect(wrapper.find('[data-test="health-data"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="health-data"]').text()).toContain('"status": "ok"');
    expect(wrapper.find('[data-test="health-data"]').text()).toContain('"bff": "ok"');
  });

  it('health view shows error when fetch fails', async () => {
    vi.spyOn(adminApi, 'fetchAdminHealth').mockRejectedValue(new Error('503'));
    const { wrapper } = await mountApp('/tabs/admin_entry/health');
    await flushPromises();
    expect(wrapper.find('[data-test="health-error"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="health-error"]').text()).toContain('503');
  });
});
