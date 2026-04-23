import { describe, it, expect, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import App from '@/App.vue';
import { useUISessionStore } from '@/stores/ui_session';
import { ADMIN_SUBTAB_IDS, ADMIN_SUBTAB_REGISTRY } from '@/domain/admin_subtabs';

async function mountAtAdmin(subtab = 'health', isAdmin = true) {
  localStorage.clear();
  setActivePinia(createPinia());
  const store = useUISessionStore();
  store.setAdmin(isAdmin);
  const router = createRouter({ history: createMemoryHistory(), routes });
  installGuards(router);
  await router.push(`/tabs/admin_entry/${subtab}`);
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  await flushPromises();
  return { wrapper, router };
}

describe('AdminLayout (L2-07)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders admin layout shell', async () => {
    const { wrapper } = await mountAtAdmin('health');
    expect(wrapper.find('[data-test="admin-layout"]').exists() || wrapper.find('.admin-layout').exists()).toBe(true);
    expect(wrapper.find('[data-test="admin-layout-nav"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="admin-layout-content"]').exists()).toBe(true);
  });

  it('renders 8 admin subtab links', async () => {
    const { wrapper } = await mountAtAdmin('health');
    const links = wrapper.findAll('[data-test^="admin-subtab-link-"]');
    expect(links.length).toBe(8);
  });

  it('each ADMIN_SUBTAB_ID has a link with its title', async () => {
    const { wrapper } = await mountAtAdmin('health');
    for (const sid of ADMIN_SUBTAB_IDS) {
      const link = wrapper.find(`[data-test="admin-subtab-link-${sid}"]`);
      expect(link.exists()).toBe(true);
      expect(link.text()).toContain(ADMIN_SUBTAB_REGISTRY[sid].title);
    }
  });

  it('active subtab has active class', async () => {
    const { wrapper } = await mountAtAdmin('users');
    const active = wrapper.find('[data-test="admin-subtab-link-users"]');
    expect(active.classes()).toContain('admin-layout__subtab--active');
    const other = wrapper.find('[data-test="admin-subtab-link-audit"]');
    expect(other.classes()).not.toContain('admin-layout__subtab--active');
  });

  it('shows non-admin warning badge when isAdmin=false', async () => {
    // Admin guard will intercept before layout mounts — simulate by manually setting
    // isAdmin AFTER routing succeeded (e.g. token expired mid-session).
    const { wrapper } = await mountAtAdmin('health', true);
    const store = useUISessionStore();
    store.setAdmin(false);
    await flushPromises();
    expect(wrapper.find('[data-test="admin-not-authorized"]').exists()).toBe(true);
  });

  it('isAdmin=true does NOT show non-admin warning', async () => {
    const { wrapper } = await mountAtAdmin('health', true);
    expect(wrapper.find('[data-test="admin-not-authorized"]').exists()).toBe(false);
  });
});
