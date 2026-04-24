import { describe, it, expect, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import App from '@/App.vue';
import { useUISessionStore } from '@/stores/ui_session';
import { TAB_IDS, TAB_REGISTRY } from '@/domain/tabs';

async function mountApp(pid: string | null = null, tabPath = '/tabs/overview') {
  setActivePinia(createPinia());
  if (pid) {
    const store = useUISessionStore();
    store.setActiveProject(pid);
  }
  const router = createRouter({ history: createMemoryHistory(), routes });
  installGuards(router);
  await router.push(tabPath);
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  await flushPromises();
  return { wrapper, router };
}

describe('MainLayout (L2-01 shell · rendered via router)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders the banner + nav + router-view slots', async () => {
    const { wrapper } = await mountApp();
    expect(wrapper.find('.main-layout').exists()).toBe(true);
    expect(wrapper.find('[data-test="main-layout-pid"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="main-layout-nav"]').exists()).toBe(true);
  });

  it('shows "无活动项目" when no pid is set', async () => {
    const { wrapper } = await mountApp(null);
    expect(wrapper.find('[data-test="main-layout-no-project"]').exists()).toBe(true);
  });

  it('shows current pid when one is active', async () => {
    const { wrapper } = await mountApp('pj-xyz');
    expect(wrapper.find('[data-test="main-layout-no-project"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="main-layout-pid"]').text()).toContain('pj-xyz');
  });

  it('renders exactly 11 tab links in nav', async () => {
    const { wrapper } = await mountApp();
    const links = wrapper
      .find('[data-test="main-layout-nav"]')
      .findAll('[data-test^="tab-link-"]');
    expect(links.length).toBe(11);
  });

  it('every TAB_ID has a matching tab link', async () => {
    const { wrapper } = await mountApp();
    for (const id of TAB_IDS) {
      expect(wrapper.find(`[data-test="tab-link-${id}"]`).exists()).toBe(true);
    }
  });

  it('tab link labels match TAB_REGISTRY titles', async () => {
    const { wrapper } = await mountApp();
    for (const id of TAB_IDS) {
      const link = wrapper.find(`[data-test="tab-link-${id}"]`);
      expect(link.text()).toContain(TAB_REGISTRY[id].title);
    }
  });

  it('active tab link gets the active class', async () => {
    const { wrapper } = await mountApp(null, '/tabs/wbs');
    const activeLink = wrapper.find('[data-test="tab-link-wbs"]');
    expect(activeLink.classes()).toContain('main-layout__tab--active');
    const inactiveLink = wrapper.find('[data-test="tab-link-overview"]');
    expect(inactiveLink.classes()).not.toContain('main-layout__tab--active');
  });

  it('renders the current tab view inside the router outlet', async () => {
    const { wrapper } = await mountApp(null, '/tabs/kb');
    expect(wrapper.find('[data-test="tab-view-kb"]').exists()).toBe(true);
  });
});
