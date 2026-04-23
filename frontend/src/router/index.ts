import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { TAB_IDS, TAB_REGISTRY, isTabId, type TabId } from '@/domain/tabs';
import { useUISessionStore } from '@/stores/ui_session';
import { getLastTab } from '@/utils/last_tab';

const MainLayout = () => import('@/views/MainTab/MainLayout.vue');

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

function buildTabChildren(): RouteRecordRaw[] {
  return TAB_IDS.map((id) => ({
    path: id,
    name: `tab:${id}`,
    component: tabComponentLoaders[id],
    meta: { tabId: id, title: TAB_REGISTRY[id].title },
  }));
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
      ...buildTabChildren(),
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

    // PM-14 cross-project guard: ?pid=<x>
    const requestedPid = typeof to.query.pid === 'string' ? to.query.pid : null;
    const access = store.guardProjectAccess(requestedPid);
    if (!access.allow) {
      console.warn('[router guard]', access.reason);
      return next({ path: `/tabs/${store.activeTabId}`, query: {} });
    }
    if (requestedPid && store.activeProjectId === null) {
      store.setActiveProject(requestedPid);
    }

    // tab validity guard
    const segments = to.path.split('/').filter(Boolean);
    if (segments[0] === 'tabs' && segments.length === 2) {
      const candidate = segments[1];
      if (!isTabId(candidate)) {
        console.warn(`[router guard] unknown tab "${candidate}", redirecting to overview`);
        return next({ path: '/tabs/overview' });
      }
      store.switchTab(candidate);
    }

    return next();
  });
}

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

installGuards(router);
