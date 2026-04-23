import { describe, it, expect } from 'vitest';
import {
  TRIM_PROFILES,
  DEFAULT_TRIM_PROFILE,
  TAB_HIDE_MAP,
  TRIM_ALIAS,
  isTrimProfile,
  isTabHiddenByProfile,
  filterVisibleTabs,
  resolveTrimAlias,
} from '@/domain/trim_profile';
import { TAB_IDS } from '@/domain/tabs';

describe('trim_profile domain (L2-06)', () => {
  it('exports 3 canonical profile enum values', () => {
    expect(TRIM_PROFILES).toEqual(['full', 'lean', 'custom']);
  });

  it('default profile is "full"', () => {
    expect(DEFAULT_TRIM_PROFILE).toBe('full');
  });

  it('TAB_HIDE_MAP has an entry for every profile', () => {
    for (const p of TRIM_PROFILES) {
      expect(TAB_HIDE_MAP[p]).toBeInstanceOf(Set);
    }
  });

  it('full profile hides no tabs', () => {
    expect(TAB_HIDE_MAP.full.size).toBe(0);
  });

  it('lean profile hides detail-heavy tabs', () => {
    expect(TAB_HIDE_MAP.lean.has('retro')).toBe(true);
    expect(TAB_HIDE_MAP.lean.has('decision_flow')).toBe(true);
    expect(TAB_HIDE_MAP.lean.has('quality')).toBe(true);
  });

  it('lean profile does NOT hide essential tabs', () => {
    expect(TAB_HIDE_MAP.lean.has('overview')).toBe(false);
    expect(TAB_HIDE_MAP.lean.has('gate')).toBe(false);
    expect(TAB_HIDE_MAP.lean.has('admin_entry')).toBe(false);
  });

  it('custom profile defaults to show all (user configures later)', () => {
    expect(TAB_HIDE_MAP.custom.size).toBe(0);
  });

  it('isTrimProfile validates', () => {
    expect(isTrimProfile('full')).toBe(true);
    expect(isTrimProfile('lean')).toBe(true);
    expect(isTrimProfile('custom')).toBe(true);
    expect(isTrimProfile('bogus')).toBe(false);
    expect(isTrimProfile('')).toBe(false);
    expect(isTrimProfile(null)).toBe(false);
    expect(isTrimProfile(undefined)).toBe(false);
  });

  it('isTabHiddenByProfile reflects map', () => {
    expect(isTabHiddenByProfile('retro', 'lean')).toBe(true);
    expect(isTabHiddenByProfile('retro', 'full')).toBe(false);
    expect(isTabHiddenByProfile('overview', 'lean')).toBe(false);
  });

  it('filterVisibleTabs removes hidden tabs only', () => {
    const full = filterVisibleTabs(TAB_IDS, 'full');
    expect(full.length).toBe(11);
    const lean = filterVisibleTabs(TAB_IDS, 'lean');
    expect(lean.length).toBe(8);
    expect(lean).not.toContain('retro');
    expect(lean).not.toContain('decision_flow');
    expect(lean).not.toContain('quality');
  });

  it('TRIM_ALIAS maps exe-plan names', () => {
    expect(TRIM_ALIAS.HEAVY).toBe('full');
    expect(TRIM_ALIAS.STANDARD).toBe('lean');
    expect(TRIM_ALIAS.LIGHT).toBe('custom');
  });

  it('resolveTrimAlias round-trips via aliases', () => {
    expect(resolveTrimAlias('HEAVY')).toBe('full');
    expect(resolveTrimAlias('STANDARD')).toBe('lean');
    expect(resolveTrimAlias('LIGHT')).toBe('custom');
    expect(resolveTrimAlias('UNKNOWN')).toBeUndefined();
  });

  it('TAB_HIDE_MAP is frozen', () => {
    expect(Object.isFrozen(TAB_HIDE_MAP)).toBe(true);
  });
});
