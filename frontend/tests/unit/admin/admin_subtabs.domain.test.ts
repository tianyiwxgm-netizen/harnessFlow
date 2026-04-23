import { describe, it, expect } from 'vitest';
import {
  ADMIN_SUBTAB_IDS,
  ADMIN_SUBTAB_COUNT,
  ADMIN_SUBTAB_REGISTRY,
  AdminSubtabContractError,
  assertAdminSubtabContract,
  isAdminSubtabId,
} from '@/domain/admin_subtabs';

describe('admin subtabs domain (L2-07)', () => {
  it('exports 8 subtab ids', () => {
    expect(ADMIN_SUBTAB_IDS.length).toBe(8);
    expect(ADMIN_SUBTAB_COUNT).toBe(8);
  });

  it('has the spec-mandated subtab ids', () => {
    expect(ADMIN_SUBTAB_IDS).toEqual([
      'users',
      'permissions',
      'audit',
      'backup',
      'config',
      'health',
      'metrics',
      'red_line_alerts',
    ]);
  });

  it('ids are unique', () => {
    expect(new Set(ADMIN_SUBTAB_IDS).size).toBe(8);
  });

  it('registry has 8 entries', () => {
    expect(Object.keys(ADMIN_SUBTAB_REGISTRY).length).toBe(8);
  });

  it('registry is frozen', () => {
    expect(Object.isFrozen(ADMIN_SUBTAB_REGISTRY)).toBe(true);
  });

  it('every entry id matches key', () => {
    for (const id of ADMIN_SUBTAB_IDS) {
      expect(ADMIN_SUBTAB_REGISTRY[id].id).toBe(id);
    }
  });

  it('every entry path is /tabs/admin_entry/<id>', () => {
    for (const id of ADMIN_SUBTAB_IDS) {
      expect(ADMIN_SUBTAB_REGISTRY[id].path).toBe(`/tabs/admin_entry/${id}`);
    }
  });

  it('order values are 1..8 permutation', () => {
    const orders = ADMIN_SUBTAB_IDS.map((id) => ADMIN_SUBTAB_REGISTRY[id].order).sort(
      (a, b) => a - b,
    );
    expect(orders).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });

  it('audit and red_line_alerts flag needsPid=true', () => {
    expect(ADMIN_SUBTAB_REGISTRY.audit.needsPid).toBe(true);
    expect(ADMIN_SUBTAB_REGISTRY.red_line_alerts.needsPid).toBe(true);
    expect(ADMIN_SUBTAB_REGISTRY.health.needsPid).toBe(false);
  });

  it('assertAdminSubtabContract passes on healthy registry', () => {
    expect(() => assertAdminSubtabContract()).not.toThrow();
  });

  it('AdminSubtabContractError has proper name', () => {
    const err = new AdminSubtabContractError('x');
    expect(err.name).toBe('AdminSubtabContractError');
  });

  it('isAdminSubtabId validates correctly', () => {
    expect(isAdminSubtabId('health')).toBe(true);
    expect(isAdminSubtabId('red_line_alerts')).toBe(true);
    expect(isAdminSubtabId('bogus')).toBe(false);
    expect(isAdminSubtabId(42)).toBe(false);
    expect(isAdminSubtabId(null)).toBe(false);
  });
});
