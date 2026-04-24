/**
 * L2-06 trim/compliance profile.
 * Spec enum `full / lean / custom` from L2-06 tech-design §2.4.
 * exe-plan WP03 adds runtime switching semantics and tab-hiding.
 */

import type { TabId } from '@/domain/tabs';

export const TRIM_PROFILES = ['full', 'lean', 'custom'] as const;
export type TrimProfile = (typeof TRIM_PROFILES)[number];

export const DEFAULT_TRIM_PROFILE: TrimProfile = 'full';

/**
 * Tabs hidden for each profile.
 * Source: exe-plan §3.3 — "某些 tab 在 LIGHT 下隐藏"; mapping chosen so that `lean`
 * hides retrospective / decision-flow / quality (detail-heavy surfaces) and `custom`
 * is opt-in (user picks tabs later via Admin).
 */
export const TAB_HIDE_MAP: Readonly<Record<TrimProfile, ReadonlySet<TabId>>> = Object.freeze({
  full: new Set<TabId>([]),
  lean: new Set<TabId>(['decision_flow', 'retro', 'quality']),
  custom: new Set<TabId>([]),
});

export function isTrimProfile(value: unknown): value is TrimProfile {
  return typeof value === 'string' && (TRIM_PROFILES as readonly string[]).includes(value);
}

export function isTabHiddenByProfile(tab: TabId, profile: TrimProfile): boolean {
  return TAB_HIDE_MAP[profile].has(tab);
}

export function filterVisibleTabs(tabs: readonly TabId[], profile: TrimProfile): TabId[] {
  const hidden = TAB_HIDE_MAP[profile];
  return tabs.filter((t) => !hidden.has(t));
}

/**
 * exe-plan aliases (LIGHT/STANDARD/HEAVY). Map to spec names so tests + UI can use either.
 */
export const TRIM_ALIAS: Readonly<Record<string, TrimProfile>> = Object.freeze({
  HEAVY: 'full',
  STANDARD: 'lean',
  LIGHT: 'custom',
});

export function resolveTrimAlias(alias: string): TrimProfile | undefined {
  return TRIM_ALIAS[alias];
}
