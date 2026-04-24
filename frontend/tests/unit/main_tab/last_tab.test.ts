import { describe, it, expect, beforeEach } from 'vitest';
import {
  LAST_TAB_STORAGE_KEY,
  DEFAULT_TAB,
  getLastTab,
  setLastTab,
  clearLastTab,
} from '@/utils/last_tab';

describe('last_tab localStorage utils', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('getLastTab returns DEFAULT_TAB when nothing stored', () => {
    expect(getLastTab()).toBe(DEFAULT_TAB);
    expect(DEFAULT_TAB).toBe('overview');
  });

  it('getLastTab returns stored valid tab id', () => {
    localStorage.setItem(LAST_TAB_STORAGE_KEY, 'wbs');
    expect(getLastTab()).toBe('wbs');
  });

  it('getLastTab falls back to DEFAULT_TAB when stored value is invalid', () => {
    localStorage.setItem(LAST_TAB_STORAGE_KEY, 'definitely_not_a_real_tab');
    expect(getLastTab()).toBe(DEFAULT_TAB);
  });

  it('setLastTab persists to localStorage', () => {
    setLastTab('gate');
    expect(localStorage.getItem(LAST_TAB_STORAGE_KEY)).toBe('gate');
    expect(getLastTab()).toBe('gate');
  });

  it('setLastTab rejects invalid tab ids', () => {
    // @ts-expect-error — testing runtime guard
    expect(() => setLastTab('bogus')).toThrow(/not a valid TabId/);
  });

  it('clearLastTab removes the value so getLastTab falls back to default', () => {
    setLastTab('kb');
    clearLastTab();
    expect(localStorage.getItem(LAST_TAB_STORAGE_KEY)).toBeNull();
    expect(getLastTab()).toBe(DEFAULT_TAB);
  });
});
