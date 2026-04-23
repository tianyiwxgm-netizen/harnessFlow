/**
 * 11-tab domain model for L1-10 L2-01.
 * Source of truth: L2-01 tech-design §2.3 TabRoute VO + §10 CFG-01/02.
 */

export const TAB_IDS = [
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
] as const;

export type TabId = (typeof TAB_IDS)[number];

export const TAB_COUNT = 11 as const;

export interface TabRoute {
  readonly id: TabId;
  readonly title: string;
  readonly order: number;
  readonly path: string;
  readonly icon: string;
}

export const TAB_REGISTRY: Readonly<Record<TabId, TabRoute>> = Object.freeze({
  overview: {
    id: 'overview',
    title: '项目总览',
    order: 1,
    path: '/tabs/overview',
    icon: 'dashboard',
  },
  gate: {
    id: 'gate',
    title: 'Gate 决策',
    order: 2,
    path: '/tabs/gate',
    icon: 'flag',
  },
  artifacts: {
    id: 'artifacts',
    title: '产出物',
    order: 3,
    path: '/tabs/artifacts',
    icon: 'folder',
  },
  progress: {
    id: 'progress',
    title: '进度',
    order: 4,
    path: '/tabs/progress',
    icon: 'activity',
  },
  wbs: {
    id: 'wbs',
    title: 'WBS',
    order: 5,
    path: '/tabs/wbs',
    icon: 'list-tree',
  },
  decision_flow: {
    id: 'decision_flow',
    title: '决策流',
    order: 6,
    path: '/tabs/decision_flow',
    icon: 'git-fork',
  },
  quality: {
    id: 'quality',
    title: '质量',
    order: 7,
    path: '/tabs/quality',
    icon: 'shield-check',
  },
  kb: {
    id: 'kb',
    title: '知识库',
    order: 8,
    path: '/tabs/kb',
    icon: 'book',
  },
  retro: {
    id: 'retro',
    title: 'Retro',
    order: 9,
    path: '/tabs/retro',
    icon: 'history',
  },
  events: {
    id: 'events',
    title: '事件流',
    order: 10,
    path: '/tabs/events',
    icon: 'list',
  },
  admin_entry: {
    id: 'admin_entry',
    title: 'Admin',
    order: 11,
    path: '/tabs/admin_entry',
    icon: 'settings',
  },
});

/**
 * Runtime hard invariant (E-10 TAB_COUNT_MISMATCH).
 * Fires on any mutation to TAB_IDS or TAB_REGISTRY length (e.g. tree-shake regression).
 */
export class TabContractViolationError extends Error {
  constructor(
    message: string,
    public readonly code: 'E-10' = 'E-10',
  ) {
    super(message);
    this.name = 'TabContractViolationError';
  }
}

export function assertTabContract(): void {
  if (TAB_IDS.length !== TAB_COUNT) {
    throw new TabContractViolationError(
      `E-10 TAB_COUNT_MISMATCH: expected ${TAB_COUNT} tabs, found ${TAB_IDS.length}`,
    );
  }
  const registryKeys = Object.keys(TAB_REGISTRY);
  if (registryKeys.length !== TAB_COUNT) {
    throw new TabContractViolationError(
      `E-10 TAB_COUNT_MISMATCH: registry has ${registryKeys.length} entries, expected ${TAB_COUNT}`,
    );
  }
  const idSet = new Set<string>(TAB_IDS);
  if (idSet.size !== TAB_COUNT) {
    throw new TabContractViolationError(
      `E-10 TAB_COUNT_MISMATCH: duplicate tab id detected, unique count=${idSet.size}`,
    );
  }
  for (const id of TAB_IDS) {
    const entry = TAB_REGISTRY[id];
    if (!entry) {
      throw new TabContractViolationError(`E-10 TAB_COUNT_MISMATCH: missing registry entry for ${id}`);
    }
    if (entry.id !== id) {
      throw new TabContractViolationError(
        `E-10 TAB_COUNT_MISMATCH: registry[${id}].id = ${entry.id}`,
      );
    }
  }
  const orders = TAB_IDS.map((id) => TAB_REGISTRY[id].order).sort((a, b) => a - b);
  for (let i = 0; i < orders.length; i++) {
    if (orders[i] !== i + 1) {
      throw new TabContractViolationError(
        `E-10 TAB_COUNT_MISMATCH: order sequence not 1..${TAB_COUNT}, got [${orders.join(',')}]`,
      );
    }
  }
}

export function isTabId(value: unknown): value is TabId {
  return typeof value === 'string' && (TAB_IDS as readonly string[]).includes(value);
}

export function getTabByOrder(order: number): TabRoute | undefined {
  return TAB_IDS.map((id) => TAB_REGISTRY[id]).find((t) => t.order === order);
}

// Fire hard invariant at module load — catches any tree-shake or accidental mutation.
assertTabContract();
