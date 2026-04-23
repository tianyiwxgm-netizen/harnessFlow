import { isTabId, type TabId } from '@/domain/tabs';

export const LAST_TAB_STORAGE_KEY = 'harnessflow.active_tab';
export const DEFAULT_TAB: TabId = 'overview';

export function getLastTab(): TabId {
  const raw = localStorage.getItem(LAST_TAB_STORAGE_KEY);
  if (raw && isTabId(raw)) {
    return raw;
  }
  return DEFAULT_TAB;
}

export function setLastTab(tab: TabId): void {
  if (!isTabId(tab)) {
    throw new Error(`setLastTab: "${tab}" is not a valid TabId`);
  }
  localStorage.setItem(LAST_TAB_STORAGE_KEY, tab);
}

export function clearLastTab(): void {
  localStorage.removeItem(LAST_TAB_STORAGE_KEY);
}
