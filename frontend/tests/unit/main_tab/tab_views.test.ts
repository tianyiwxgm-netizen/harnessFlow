import { describe, it, expect, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes, installGuards } from '@/router/index';
import App from '@/App.vue';
import { TAB_IDS, TAB_REGISTRY } from '@/domain/tabs';
import { useUISessionStore } from '@/stores/ui_session';

describe('11 placeholder tab views render correctly (via router)', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  for (const id of TAB_IDS) {
    it(`tab view "${id}" renders its title + pid indicator`, async () => {
      const router = createRouter({ history: createMemoryHistory(), routes });
      installGuards(router);
      const store = useUISessionStore();
      store.setActiveProject('pj-test');
      await router.push(`/tabs/${id}`);
      await router.isReady();

      const wrapper = mount(App, { global: { plugins: [router] } });
      await flushPromises();

      const tabView = wrapper.find(`[data-test="tab-view-${id}"]`);
      expect(tabView.exists()).toBe(true);
      expect(tabView.find('h2').text()).toBe(TAB_REGISTRY[id].title);
      expect(tabView.find('[data-test="tab-view-pid"]').text()).toContain('pj-test');
    });
  }
});
