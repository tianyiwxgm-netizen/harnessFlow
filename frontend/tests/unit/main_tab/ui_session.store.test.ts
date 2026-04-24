import { describe, it, expect, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useUISessionStore } from '@/stores/ui_session';
import { TAB_IDS } from '@/domain/tabs';
import { LAST_TAB_STORAGE_KEY } from '@/utils/last_tab';

describe('UISession Pinia store (L2-01 AR)', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  it('initialises with no active project', () => {
    const store = useUISessionStore();
    expect(store.activeProjectId).toBeNull();
    expect(store.hasActiveProject).toBe(false);
  });

  it('initial activeTabId is the default overview tab', () => {
    const store = useUISessionStore();
    expect(store.activeTabId).toBe('overview');
  });

  it('restores activeTabId from localStorage on init', () => {
    localStorage.setItem(LAST_TAB_STORAGE_KEY, 'wbs');
    const store = useUISessionStore();
    expect(store.activeTabId).toBe('wbs');
  });

  it('tabOrder contains exactly the 11 canonical tab ids', () => {
    const store = useUISessionStore();
    expect(store.orderedTabIds.length).toBe(11);
    expect(Array.from(store.orderedTabIds)).toEqual(Array.from(TAB_IDS));
  });

  it('setActiveProject sets pid', () => {
    const store = useUISessionStore();
    store.setActiveProject('pj-123');
    expect(store.activeProjectId).toBe('pj-123');
    expect(store.hasActiveProject).toBe(true);
  });

  it('setActiveProject rejects empty string', () => {
    const store = useUISessionStore();
    expect(() => store.setActiveProject('')).toThrow(/must be non-empty/);
  });

  it('clearActiveProject nulls the pid', () => {
    const store = useUISessionStore();
    store.setActiveProject('pj-abc');
    store.clearActiveProject();
    expect(store.activeProjectId).toBeNull();
  });

  it('switchTab updates state and persists', () => {
    const store = useUISessionStore();
    store.switchTab('kb');
    expect(store.activeTabId).toBe('kb');
    expect(localStorage.getItem(LAST_TAB_STORAGE_KEY)).toBe('kb');
  });

  it('switchTab rejects invalid tab id', () => {
    const store = useUISessionStore();
    // @ts-expect-error — runtime guard test
    expect(() => store.switchTab('not_a_tab')).toThrow(/not a valid TabId/);
  });

  it('switchTab to the same tab is a no-op (does not rewrite localStorage)', () => {
    const store = useUISessionStore();
    store.switchTab('gate');
    localStorage.setItem(LAST_TAB_STORAGE_KEY, 'TAMPERED');
    store.switchTab('gate');
    expect(localStorage.getItem(LAST_TAB_STORAGE_KEY)).toBe('TAMPERED');
  });

  it('guardProjectAccess allows null (no requested pid)', () => {
    const store = useUISessionStore();
    store.setActiveProject('pj-x');
    expect(store.guardProjectAccess(null)).toEqual({ allow: true });
  });

  it('guardProjectAccess allows when no active project yet (first-use)', () => {
    const store = useUISessionStore();
    expect(store.guardProjectAccess('pj-first')).toEqual({ allow: true });
  });

  it('guardProjectAccess allows matching pid', () => {
    const store = useUISessionStore();
    store.setActiveProject('pj-x');
    expect(store.guardProjectAccess('pj-x')).toEqual({ allow: true });
  });

  it('guardProjectAccess denies mismatched pid with reason (PM-14)', () => {
    const store = useUISessionStore();
    store.setActiveProject('pj-x');
    const result = store.guardProjectAccess('pj-y');
    expect(result.allow).toBe(false);
    if (!result.allow) {
      expect(result.reason).toContain('cross_project_access_denied');
      expect(result.reason).toContain('pj-y');
      expect(result.reason).toContain('pj-x');
    }
  });

  it('setTheme updates preferences', () => {
    const store = useUISessionStore();
    store.setTheme('dark');
    expect(store.preferences.theme).toBe('dark');
  });
});
