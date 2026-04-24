import { describe, it, expect, beforeEach } from 'vitest';
import {
  TRIM_PROFILE_STORAGE_KEY,
  getStoredTrimProfile,
  setStoredTrimProfile,
  clearStoredTrimProfile,
} from '@/utils/trim_profile_storage';

describe('trim_profile_storage (localStorage persist)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('getStoredTrimProfile falls back to full when nothing stored', () => {
    expect(getStoredTrimProfile()).toBe('full');
  });

  it('setStoredTrimProfile persists valid values', () => {
    setStoredTrimProfile('lean');
    expect(localStorage.getItem(TRIM_PROFILE_STORAGE_KEY)).toBe('lean');
    expect(getStoredTrimProfile()).toBe('lean');
  });

  it('setStoredTrimProfile rejects invalid values', () => {
    // @ts-expect-error — testing runtime guard
    expect(() => setStoredTrimProfile('bogus')).toThrow(/not a valid TrimProfile/);
  });

  it('clearStoredTrimProfile removes stored value', () => {
    setStoredTrimProfile('custom');
    clearStoredTrimProfile();
    expect(localStorage.getItem(TRIM_PROFILE_STORAGE_KEY)).toBeNull();
    expect(getStoredTrimProfile()).toBe('full');
  });

  it('getStoredTrimProfile falls back when stored value is corrupt', () => {
    localStorage.setItem(TRIM_PROFILE_STORAGE_KEY, 'CORRUPT_PROFILE_VAL');
    expect(getStoredTrimProfile()).toBe('full');
  });
});
