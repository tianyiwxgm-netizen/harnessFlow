import { describe, it, expect } from 'vitest';
import {
  TAB_IDS,
  TAB_COUNT,
  TAB_REGISTRY,
  TabContractViolationError,
  assertTabContract,
  isTabId,
  getTabByOrder,
} from '@/domain/tabs';

describe('L2-01 · 11-tab domain contract', () => {
  it('exports exactly 11 tab ids', () => {
    expect(TAB_IDS.length).toBe(11);
    expect(TAB_COUNT).toBe(11);
  });

  it('has the spec-mandated tab ids in spec order', () => {
    expect(TAB_IDS).toEqual([
      'overview',
      'gate',
      'artifacts',
      'progress',
      'wbs',
      'decision_flow',
      'quality',
      'kb',
      'retro',
      'events',
      'admin_entry',
    ]);
  });

  it('has unique tab ids', () => {
    const set = new Set(TAB_IDS);
    expect(set.size).toBe(TAB_IDS.length);
  });

  it('TAB_REGISTRY has exactly 11 entries', () => {
    expect(Object.keys(TAB_REGISTRY).length).toBe(11);
  });

  it('each TAB_REGISTRY entry has id equal to key', () => {
    for (const id of TAB_IDS) {
      expect(TAB_REGISTRY[id].id).toBe(id);
    }
  });

  it('each tab route has a non-empty title and icon', () => {
    for (const id of TAB_IDS) {
      expect(TAB_REGISTRY[id].title.length).toBeGreaterThan(0);
      expect(TAB_REGISTRY[id].icon.length).toBeGreaterThan(0);
    }
  });

  it('each tab path starts with /tabs/', () => {
    for (const id of TAB_IDS) {
      expect(TAB_REGISTRY[id].path).toBe(`/tabs/${id}`);
    }
  });

  it('tab orders form a permutation of 1..11', () => {
    const orders = TAB_IDS.map((id) => TAB_REGISTRY[id].order).sort((a, b) => a - b);
    expect(orders).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
  });

  it('TAB_REGISTRY is frozen (immutable)', () => {
    expect(Object.isFrozen(TAB_REGISTRY)).toBe(true);
  });

  it('assertTabContract passes on healthy registry', () => {
    expect(() => assertTabContract()).not.toThrow();
  });

  it('TabContractViolationError has code E-10', () => {
    const err = new TabContractViolationError('test');
    expect(err.code).toBe('E-10');
    expect(err.name).toBe('TabContractViolationError');
  });

  it('isTabId returns true for valid tab ids', () => {
    expect(isTabId('overview')).toBe(true);
    expect(isTabId('admin_entry')).toBe(true);
  });

  it('isTabId returns false for invalid values', () => {
    expect(isTabId('unknown')).toBe(false);
    expect(isTabId('')).toBe(false);
    expect(isTabId(undefined)).toBe(false);
    expect(isTabId(null)).toBe(false);
    expect(isTabId(42)).toBe(false);
  });

  it('getTabByOrder returns the tab with matching order', () => {
    expect(getTabByOrder(1)?.id).toBe('overview');
    expect(getTabByOrder(11)?.id).toBe('admin_entry');
  });

  it('getTabByOrder returns undefined for out-of-range order', () => {
    expect(getTabByOrder(0)).toBeUndefined();
    expect(getTabByOrder(12)).toBeUndefined();
    expect(getTabByOrder(-1)).toBeUndefined();
  });
});
