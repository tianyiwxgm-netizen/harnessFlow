import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { TAB_IDS, TAB_REGISTRY, isTabId, type TabId } from '@/domain/tabs';
import {
  ADMIN_SUBTAB_IDS,
  ADMIN_SUBTAB_REGISTRY,
  isAdminSubtabId,
  type AdminSubtabId,
} from '@/domain/admin_subtabs';
import { useUISessionStore } from '@/stores/ui_session';
import { getLastTab } from '@/utils/last_tab';

const MainLayout = () => import('@/views/MainTab/MainLayout.vue');
const AdminLayout = () => import('@/views/Admin/AdminLayout.vue');

const tabComponentLoaders: Record<TabId, () => Promise<unknown>> = {
  overview: () => import('@/views/MainTab/OverviewView.vue'),
  gate: () => import('@/views/MainTab/GateView.vue'),
  artifacts: () => import('@/views/MainTab/ArtifactsView.vue'),
  progress: () => import('@/views/MainTab/ProgressView.vue'),
  wbs: () => import('@/views/MainTab/WbsView.vue'),
  decision_flow: () => import('@/views/MainTab/DecisionFlowView.vue'),
  quality: () => import('@/views/MainTab/QualityView.vue'),
  kb: () => import('@/views/MainTab/KbView.vue'),
  retro: () => import('@/views/MainTab/RetroView.vue'),
  events: () => import('@/views/MainTab/EventsView.vue'),
  admin_entry: () => import('@/views/MainTab/AdminEntryView.vue'),
};

const adminSubtabLoaders: Record<AdminSubtabId, () => Promise<unknown>> = {
  users: () => import('@/views/Admin/UsersView.vue'),
  permissions: () => import('@/views/Admin/PermissionsView.vue'),
  audit: () => import('@/views/Admin/AuditView.vue'),
  backup: () => import('@/views/Admin/BackupView.vue'),
  config: () => import('@/views/Admin/ConfigView.vue'),
  health: () => import('@/views/Admin/HealthView.vue'),
  metrics: () => import('@/views/Admin/MetricsView.vue'),
  red_line_alerts: () => import('@/views/Admin/RedLineAlertsView.vue'),
};

function buildMainTabChildren(): RouteRecordRaw[] {
  const simpleTabs = TAB_IDS.filter((id) => id !== 'admin_entry').map((id) => ({
    path: id,
    name: `tab:${id}`,
    component: tabComponentLoaders[id],
    meta: { tabId: id, title: TAB_REGISTRY[id].title },
  }));

  const adminRoute: RouteRecordRaw = {
    path: 'admin_entry',
    component: AdminLayout,
    meta: { tabId: 'admin_entry', title: TAB_REGISTRY.admin_entry.title, requiresAdmin: true },
    children: [
      { path: '', redirect: { path: '/tabs/admin_entry/health' } },
      ...ADMIN_SUBTAB_IDS.map((sid) => ({
        path: sid,
        name: `admin:${sid}`,
        component: adminSubtabLoaders[sid],
        meta: {
          tabId: 'admin_entry' as TabId,
          adminSubtabId: sid,
          title: ADMIN_SUBTAB_REGISTRY[sid].title,
          requiresAdmin: true,
        },
      })),
      {
        path: ':invalid(.*)',
        redirect: { path: '/tabs/admin_entry/health' },
      },
    ],
  };

  return [...simpleTabs, adminRoute];
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => ({ path: `/tabs/${getLastTab()}` }),
  },
  {
    path: '/tabs',
    component: MainLayout,
    children: [
      { path: '', redirect: () => ({ path: `/tabs/${getLastTab()}` }) },
      ...buildMainTabChildren(),
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    redirect: '/',
  },
];

export function installGuards(router: ReturnType<typeof createRouter>): void {
  router.beforeEach((to, _from, next) => {
    const store = useUISessionStore();

    // PM-14 cross-project guard.
    const requestedPid = typeof to.query.pid === 'string' ? to.query.pid : null;
    const access = store.guardProjectAccess(requestedPid);
    if (!access.allow) {
      console.warn('[router guard]', access.reason);
      return next({ path: `/tabs/${store.activeTabId}`, query: {} });
    }
    if (requestedPid && store.activeProjectId === null) {
      store.setActiveProject(requestedPid);
    }

    // Admin guard (L2-07): any matched route with meta.requiresAdmin=true.
    const needsAdmin = to.matched.some((r) => r.meta?.requiresAdmin === true);
    if (needsAdmin && !store.isAdmin) {
      console.warn('[router guard] non-admin blocked from', to.path);
      return next({ path: '/tabs/overview' });
    }

    // Tab-level state sync (segment 1 == top-level tab).
    const segments = to.path.split('/').filter(Boolean);
    if (segments[0] === 'tabs' && segments.length >= 2) {
      const candidate = segments[1];
      if (!isTabId(candidate)) {
        console.warn(`[router guard] unknown tab "${candidate}", redirecting to overview`);
        return next({ path: '/tabs/overview' });
      }
      store.switchTab(candidate);

      // Optional admin subtab validity.
      if (candidate === 'admin_entry' && segments.length === 3) {
        const sub = segments[2];
        if (!isAdminSubtabId(sub)) {
          console.warn(`[router guard] unknown admin subtab "${sub}", redirecting to health`);
          return next({ path: '/tabs/admin_entry/health' });
        }
      }
    }

    return next();
  });
}

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

installGuards(router);
