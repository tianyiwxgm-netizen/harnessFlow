import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import TrimProfileSwitcher from '@/views/TrimConfig/TrimProfileSwitcher.vue';
import { useTrimProfileStore } from '@/stores/trim_profile';
import * as api from '@/api/trim_profile';

describe('TrimProfileSwitcher', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('renders the switcher root + select', () => {
    const wrapper = mount(TrimProfileSwitcher);
    expect(wrapper.find('[data-test="trim-switcher"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="trim-switcher-select"]').exists()).toBe(true);
  });

  it('renders 3 options (full/lean/custom)', () => {
    const wrapper = mount(TrimProfileSwitcher);
    expect(wrapper.find('[data-test="trim-option-full"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="trim-option-lean"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="trim-option-custom"]').exists()).toBe(true);
  });

  it('option labels include HEAVY/STANDARD/LIGHT aliases', () => {
    const wrapper = mount(TrimProfileSwitcher);
    expect(wrapper.find('[data-test="trim-option-full"]').text()).toContain('HEAVY');
    expect(wrapper.find('[data-test="trim-option-lean"]').text()).toContain('STANDARD');
    expect(wrapper.find('[data-test="trim-option-custom"]').text()).toContain('LIGHT');
  });

  it('selecting an option calls store.switchProfile + patchConfigProfile', async () => {
    const patchSpy = vi
      .spyOn(api, 'patchConfigProfile')
      .mockResolvedValue({ profile: 'lean', synced: true });
    const wrapper = mount(TrimProfileSwitcher);
    const select = wrapper.get('[data-test="trim-switcher-select"]');
    await select.setValue('lean');
    await flushPromises();
    expect(patchSpy).toHaveBeenCalledWith('lean');
    const store = useTrimProfileStore();
    expect(store.current).toBe('lean');
    expect(store.lastSyncError).toBeNull();
    expect(store.lastSyncedAt).not.toBeNull();
  });

  it('shows "已同步" after successful sync', async () => {
    vi.spyOn(api, 'patchConfigProfile').mockResolvedValue({ profile: 'lean', synced: true });
    const wrapper = mount(TrimProfileSwitcher);
    await wrapper.get('[data-test="trim-switcher-select"]').setValue('lean');
    await flushPromises();
    expect(wrapper.find('[data-test="trim-switcher-ok"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="trim-switcher-err"]').exists()).toBe(false);
  });

  it('shows error when backend sync fails', async () => {
    vi.spyOn(api, 'patchConfigProfile').mockRejectedValue(new Error('offline'));
    const wrapper = mount(TrimProfileSwitcher);
    await wrapper.get('[data-test="trim-switcher-select"]').setValue('custom');
    await flushPromises();
    expect(wrapper.find('[data-test="trim-switcher-err"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="trim-switcher-err"]').text()).toContain('offline');
  });

  it('keeps local switch even when backend sync fails (optimistic UI)', async () => {
    vi.spyOn(api, 'patchConfigProfile').mockRejectedValue(new Error('offline'));
    const wrapper = mount(TrimProfileSwitcher);
    await wrapper.get('[data-test="trim-switcher-select"]').setValue('custom');
    await flushPromises();
    const store = useTrimProfileStore();
    expect(store.current).toBe('custom');
  });

  it('re-syncs selected value when store.current changes externally', async () => {
    const wrapper = mount(TrimProfileSwitcher);
    const store = useTrimProfileStore();
    store.switchProfile('lean');
    await flushPromises();
    const select = wrapper.get('[data-test="trim-switcher-select"]')
      .element as HTMLSelectElement;
    expect(select.value).toBe('lean');
  });
});
