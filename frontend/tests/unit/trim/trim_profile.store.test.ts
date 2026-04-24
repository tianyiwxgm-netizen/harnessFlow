import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useTrimProfileStore } from '@/stores/trim_profile';
import { TRIM_PROFILE_STORAGE_KEY } from '@/utils/trim_profile_storage';
import { TAB_IDS } from '@/domain/tabs';

describe('TrimProfile Pinia store (L2-06)', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('initialises to full profile by default', () => {
    const store = useTrimProfileStore();
    expect(store.current).toBe('full');
    expect(store.isHeavy).toBe(true);
    expect(store.isLean).toBe(false);
    expect(store.isCustom).toBe(false);
  });

  it('restores stored profile on init', () => {
    localStorage.setItem(TRIM_PROFILE_STORAGE_KEY, 'lean');
    const store = useTrimProfileStore();
    expect(store.current).toBe('lean');
    expect(store.isLean).toBe(true);
  });

  it('switchProfile updates state + localStorage', () => {
    const store = useTrimProfileStore();
    store.switchProfile('custom');
    expect(store.current).toBe('custom');
    expect(store.isCustom).toBe(true);
    expect(localStorage.getItem(TRIM_PROFILE_STORAGE_KEY)).toBe('custom');
  });

  it('switchProfile rejects invalid value', () => {
    const store = useTrimProfileStore();
    // @ts-expect-error — runtime guard test
    expect(() => store.switchProfile('hybrid')).toThrow(/not a valid TrimProfile/);
  });

  it('switchProfile is a no-op when profile unchanged', () => {
    const store = useTrimProfileStore();
    store.switchProfile('lean');
    localStorage.setItem(TRIM_PROFILE_STORAGE_KEY, 'TAMPERED');
    store.switchProfile('lean');
    expect(localStorage.getItem(TRIM_PROFILE_STORAGE_KEY)).toBe('TAMPERED');
  });

  it('switchProfile resets sync markers', () => {
    const store = useTrimProfileStore();
    store.markSyncSuccess();
    store.switchProfile('custom');
    expect(store.lastSyncedAt).toBeNull();
    expect(store.lastSyncError).toBeNull();
  });

  it('markSyncSuccess updates lastSyncedAt', () => {
    const store = useTrimProfileStore();
    const before = Date.now();
    store.markSyncSuccess();
    expect(store.lastSyncedAt).toBeGreaterThanOrEqual(before);
    expect(store.lastSyncError).toBeNull();
  });

  it('markSyncError records message', () => {
    const store = useTrimProfileStore();
    store.markSyncError('network timeout');
    expect(store.lastSyncError).toBe('network timeout');
  });

  it('hiddenTabs getter reflects current profile', () => {
    const store = useTrimProfileStore();
    expect(store.hiddenTabs.size).toBe(0);
    store.switchProfile('lean');
    expect(store.hiddenTabs.has('retro')).toBe(true);
  });

  it('visibleTabs getter filters hidden tabs', () => {
    const store = useTrimProfileStore();
    store.switchProfile('lean');
    const visible = store.visibleTabs(TAB_IDS);
    expect(visible.length).toBe(8);
    expect(visible).not.toContain('retro');
  });

  it('resetToDefault returns to full', () => {
    const store = useTrimProfileStore();
    store.switchProfile('lean');
    store.resetToDefault();
    expect(store.current).toBe('full');
  });
});
