import { describe, it, expect, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import App from '@/App.vue';
import { useTrimProfileStore } from '@/stores/trim_profile';

async function mountAppWithProfile(profile: 'full' | 'lean' | 'custom') {
  localStorage.clear();
  setActivePinia(createPinia());
  const store = useTrimProfileStore();
  store.switchProfile(profile);
  const router = createRouter({ history: createMemoryHistory(), routes });
  installGuards(router);
  await router.push('/tabs/overview');
  await router.isReady();
  const wrapper = mount(App, { global: { plugins: [router] } });
  await flushPromises();
  return wrapper;
}

describe('MainLayout nav filtering by trim profile', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('full profile shows all 11 tabs', async () => {
    const wrapper = await mountAppWithProfile('full');
    const links = wrapper
      .find('[data-test="main-layout-nav"]')
      .findAll('[data-test^="tab-link-"]');
    expect(links.length).toBe(11);
  });

  it('lean profile hides retro / decision_flow / quality (8 visible)', async () => {
    const wrapper = await mountAppWithProfile('lean');
    const links = wrapper
      .find('[data-test="main-layout-nav"]')
      .findAll('[data-test^="tab-link-"]');
    expect(links.length).toBe(8);
    expect(wrapper.find('[data-test="tab-link-retro"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="tab-link-decision_flow"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="tab-link-quality"]').exists()).toBe(false);
  });

  it('lean profile still shows essential tabs', async () => {
    const wrapper = await mountAppWithProfile('lean');
    expect(wrapper.find('[data-test="tab-link-overview"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="tab-link-gate"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="tab-link-admin_entry"]').exists()).toBe(true);
  });

  it('custom profile shows all tabs by default', async () => {
    const wrapper = await mountAppWithProfile('custom');
    const links = wrapper
      .find('[data-test="main-layout-nav"]')
      .findAll('[data-test^="tab-link-"]');
    expect(links.length).toBe(11);
  });

  it('trim switcher is visible in the top banner', async () => {
    const wrapper = await mountAppWithProfile('full');
    expect(wrapper.find('[data-test="trim-switcher"]').exists()).toBe(true);
  });

  it('reactively updates tab list when profile changes', async () => {
    const wrapper = await mountAppWithProfile('full');
    expect(
      wrapper.find('[data-test="main-layout-nav"]').findAll('[data-test^="tab-link-"]').length,
    ).toBe(11);
    const store = useTrimProfileStore();
    store.switchProfile('lean');
    await flushPromises();
    expect(
      wrapper.find('[data-test="main-layout-nav"]').findAll('[data-test^="tab-link-"]').length,
    ).toBe(8);
  });
});
