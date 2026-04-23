/**
 * L2-07 Admin 子 tab · 8 个
 * Source: exe-plan Dev-θ §3.4 WP-θ-04.
 */

export const ADMIN_SUBTAB_IDS = [
  'users',
  'permissions',
  'audit',
  'backup',
  'config',
  'health',
  'metrics',
  'red_line_alerts',
] as const;

export type AdminSubtabId = (typeof ADMIN_SUBTAB_IDS)[number];

export const ADMIN_SUBTAB_COUNT = 8 as const;

export interface AdminSubtabRoute {
  readonly id: AdminSubtabId;
  readonly title: string;
  readonly order: number;
  readonly path: string;
  readonly needsPid: boolean;
}

export const ADMIN_SUBTAB_REGISTRY: Readonly<Record<AdminSubtabId, AdminSubtabRoute>> = Object.freeze({
  users: {
    id: 'users',
    title: '用户',
    order: 1,
    path: '/tabs/admin_entry/users',
    needsPid: false,
  },
  permissions: {
    id: 'permissions',
    title: '权限',
    order: 2,
    path: '/tabs/admin_entry/permissions',
    needsPid: false,
  },
  audit: {
    id: 'audit',
    title: '审计',
    order: 3,
    path: '/tabs/admin_entry/audit',
    needsPid: true,
  },
  backup: {
    id: 'backup',
    title: '备份',
    order: 4,
    path: '/tabs/admin_entry/backup',
    needsPid: false,
  },
  config: {
    id: 'config',
    title: '配置',
    order: 5,
    path: '/tabs/admin_entry/config',
    needsPid: false,
  },
  health: {
    id: 'health',
    title: '健康',
    order: 6,
    path: '/tabs/admin_entry/health',
    needsPid: false,
  },
  metrics: {
    id: 'metrics',
    title: '指标',
    order: 7,
    path: '/tabs/admin_entry/metrics',
    needsPid: false,
  },
  red_line_alerts: {
    id: 'red_line_alerts',
    title: '红线告警',
    order: 8,
    path: '/tabs/admin_entry/red_line_alerts',
    needsPid: true,
  },
});

export class AdminSubtabContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AdminSubtabContractError';
  }
}

export function assertAdminSubtabContract(): void {
  if (ADMIN_SUBTAB_IDS.length !== ADMIN_SUBTAB_COUNT) {
    throw new AdminSubtabContractError(
      `expected ${ADMIN_SUBTAB_COUNT} admin subtabs, found ${ADMIN_SUBTAB_IDS.length}`,
    );
  }
  if (Object.keys(ADMIN_SUBTAB_REGISTRY).length !== ADMIN_SUBTAB_COUNT) {
    throw new AdminSubtabContractError(
      `registry size mismatch: ${Object.keys(ADMIN_SUBTAB_REGISTRY).length}`,
    );
  }
  for (const id of ADMIN_SUBTAB_IDS) {
    const e = ADMIN_SUBTAB_REGISTRY[id];
    if (!e || e.id !== id) {
      throw new AdminSubtabContractError(`registry[${id}] malformed`);
    }
  }
}

export function isAdminSubtabId(value: unknown): value is AdminSubtabId {
  return typeof value === 'string' && (ADMIN_SUBTAB_IDS as readonly string[]).includes(value);
}

assertAdminSubtabContract();
