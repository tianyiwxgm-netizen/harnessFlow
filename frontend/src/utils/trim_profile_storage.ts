import {
  DEFAULT_TRIM_PROFILE,
  isTrimProfile,
  type TrimProfile,
} from '@/domain/trim_profile';

export const TRIM_PROFILE_STORAGE_KEY = 'harnessflow.trim_profile';

export function getStoredTrimProfile(): TrimProfile {
  const raw = localStorage.getItem(TRIM_PROFILE_STORAGE_KEY);
  if (raw && isTrimProfile(raw)) {
    return raw;
  }
  return DEFAULT_TRIM_PROFILE;
}

export function setStoredTrimProfile(profile: TrimProfile): void {
  if (!isTrimProfile(profile)) {
    throw new Error(`setStoredTrimProfile: "${profile}" is not a valid TrimProfile`);
  }
  localStorage.setItem(TRIM_PROFILE_STORAGE_KEY, profile);
}

export function clearStoredTrimProfile(): void {
  localStorage.removeItem(TRIM_PROFILE_STORAGE_KEY);
}
