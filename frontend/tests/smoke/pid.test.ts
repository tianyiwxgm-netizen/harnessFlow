import { describe, it, expect, beforeEach } from 'vitest';
import { getActivePid, setActivePid, clearActivePid, PID_STORAGE_KEY } from '@/utils/pid';

describe('pid utils (PM-14)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when no pid is set', () => {
    expect(getActivePid()).toBeNull();
  });

  it('persists and reads pid from localStorage', () => {
    setActivePid('pj-abc123');
    expect(localStorage.getItem(PID_STORAGE_KEY)).toBe('pj-abc123');
    expect(getActivePid()).toBe('pj-abc123');
  });

  it('clears pid', () => {
    setActivePid('pj-abc123');
    clearActivePid();
    expect(getActivePid()).toBeNull();
    expect(localStorage.getItem(PID_STORAGE_KEY)).toBeNull();
  });

  it('rejects empty string pid', () => {
    expect(() => setActivePid('')).toThrow(/pid must be non-empty/);
  });
});
