import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import App from '@/App.vue';
import { createPinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';
import { routes } from '@/router/index';

describe('App.vue smoke', () => {
  it('mounts with router + pinia and renders <router-view />', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes });
    const pinia = createPinia();
    await router.push('/');
    await router.isReady();
    const wrapper = mount(App, { global: { plugins: [router, pinia] } });
    expect(wrapper.html()).toContain('data-test="app-root"');
  });
});
