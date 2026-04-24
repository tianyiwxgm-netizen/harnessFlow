import { defineStore } from 'pinia';
import { TAB_IDS, type TabId, isTabId } from '@/domain/tabs';
import { getLastTab, setLastTab } from '@/utils/last_tab';

export type Theme = 'light' | 'dark' | 'auto';

export interface PreferenceBundle {
  tabOrder: readonly TabId[];
  theme: Theme;
}

interface UISessionState {
  activeProjectId: string | null;
  activeTabId: TabId;
  preferences: PreferenceBundle;
  /**
   * L2-07 admin guard flag. Default true in WP04 demo mode; real auth (OIDC / session)
   * replaces this in a future WP via a boot-time hook that flips it based on user claims.
   */
  isAdmin: boolean;
}

export const useUISessionStore = defineStore('ui_session', {
  state: (): UISessionState => ({
    activeProjectId: null,
    activeTabId: getLastTab(),
    preferences: {
      tabOrder: TAB_IDS,
      theme: 'auto',
    },
    isAdmin: true,
  }),

  getters: {
    hasActiveProject: (state): boolean => state.activeProjectId !== null,
    orderedTabIds: (state): readonly TabId[] => state.preferences.tabOrder,
  },

  actions: {
    setActiveProject(pid: string): void {
      if (!pid) {
        throw new Error('setActiveProject: pid must be non-empty');
      }
      this.activeProjectId = pid;
    },

    clearActiveProject(): void {
      this.activeProjectId = null;
    },

    /**
     * Switch the active tab with guards:
     *  - tab id must be a valid TabId (E-10 defence)
     *  - persists to localStorage
     */
    switchTab(tab: TabId): void {
      if (!isTabId(tab)) {
        throw new Error(`switchTab: "${tab}" is not a valid TabId`);
      }
      if (this.activeTabId === tab) {
        return;
      }
      this.activeTabId = tab;
      setLastTab(tab);
    },

    /**
     * Cross-project access guard (PM-14).
     * Returns `{ allow: true }` if requestedPid matches the active project (or no active project yet),
     * otherwise `{ allow: false, reason }`.
     */
    guardProjectAccess(requestedPid: string | null): { allow: true } | { allow: false; reason: string } {
      if (requestedPid === null || requestedPid === undefined) {
        return { allow: true };
      }
      if (this.activeProjectId === null) {
        // first-use: adopt the requested pid
        return { allow: true };
      }
      if (requestedPid === this.activeProjectId) {
        return { allow: true };
      }
      return {
        allow: false,
        reason: `cross_project_access_denied: requested=${requestedPid}, active=${this.activeProjectId}`,
      };
    },

    setTheme(theme: Theme): void {
      this.preferences.theme = theme;
    },

    setAdmin(flag: boolean): void {
      this.isAdmin = flag;
    },
  },
});
