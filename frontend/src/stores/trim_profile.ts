import { defineStore } from 'pinia';
import {
  DEFAULT_TRIM_PROFILE,
  TAB_HIDE_MAP,
  filterVisibleTabs,
  isTrimProfile,
  type TrimProfile,
} from '@/domain/trim_profile';
import {
  getStoredTrimProfile,
  setStoredTrimProfile,
} from '@/utils/trim_profile_storage';
import type { TabId } from '@/domain/tabs';

interface TrimProfileState {
  current: TrimProfile;
  lastSyncedAt: number | null;
  lastSyncError: string | null;
}

export const useTrimProfileStore = defineStore('trim_profile', {
  state: (): TrimProfileState => ({
    current: getStoredTrimProfile(),
    lastSyncedAt: null,
    lastSyncError: null,
  }),

  getters: {
    hiddenTabs: (state): ReadonlySet<TabId> => TAB_HIDE_MAP[state.current],
    visibleTabs() {
      return (allTabs: readonly TabId[]) => filterVisibleTabs(allTabs, this.current);
    },
    isHeavy: (state): boolean => state.current === 'full',
    isLean: (state): boolean => state.current === 'lean',
    isCustom: (state): boolean => state.current === 'custom',
  },

  actions: {
    /**
     * Switch profile locally (sync), persist to localStorage.
     * Backend sync is caller's responsibility (see markSyncSuccess / markSyncError).
     */
    switchProfile(profile: TrimProfile): void {
      if (!isTrimProfile(profile)) {
        throw new Error(`switchProfile: "${profile}" is not a valid TrimProfile`);
      }
      if (this.current === profile) {
        return;
      }
      this.current = profile;
      setStoredTrimProfile(profile);
      this.lastSyncedAt = null;
      this.lastSyncError = null;
    },

    markSyncSuccess(): void {
      this.lastSyncedAt = Date.now();
      this.lastSyncError = null;
    },

    markSyncError(message: string): void {
      this.lastSyncError = message;
    },

    resetToDefault(): void {
      this.switchProfile(DEFAULT_TRIM_PROFILE);
    },
  },
});
