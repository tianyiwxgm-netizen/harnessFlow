<template>
  <div
    data-test="main-layout"
    class="main-layout"
  >
    <header class="main-layout__banner">
      <div class="main-layout__brand">
        <strong>HarnessFlow</strong>
      </div>
      <div
        class="main-layout__pid"
        :class="{ 'main-layout__pid--active': uiSession.hasActiveProject }"
        data-test="main-layout-pid"
      >
        <span v-if="uiSession.hasActiveProject">
          项目: {{ uiSession.activeProjectId }}
        </span>
        <span
          v-else
          data-test="main-layout-no-project"
        >无活动项目</span>
      </div>
    </header>
    <nav
      class="main-layout__nav"
      data-test="main-layout-nav"
    >
      <ul>
        <li
          v-for="tabId in uiSession.orderedTabIds"
          :key="tabId"
          :data-test="`tab-link-${tabId}`"
          :class="{
            'main-layout__tab': true,
            'main-layout__tab--active': uiSession.activeTabId === tabId,
          }"
        >
          <RouterLink :to="TAB_REGISTRY[tabId].path">
            {{ TAB_REGISTRY[tabId].title }}
          </RouterLink>
        </li>
      </ul>
    </nav>
    <main class="main-layout__content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { useUISessionStore } from '@/stores/ui_session';
import { TAB_REGISTRY } from '@/domain/tabs';

const uiSession = useUISessionStore();
</script>

<style scoped>
.main-layout {
  display: grid;
  grid-template-rows: auto auto 1fr;
  min-height: 100vh;
  background: #f8fafc;
}
.main-layout__banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: #1e293b;
  color: white;
}
.main-layout__pid {
  font-size: 0.875rem;
  color: #94a3b8;
}
.main-layout__pid--active {
  color: #4ade80;
  font-weight: 600;
}
.main-layout__nav ul {
  display: flex;
  gap: 0.25rem;
  padding: 0 1rem;
  margin: 0;
  list-style: none;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.main-layout__tab a {
  display: block;
  padding: 0.75rem 1rem;
  color: #475569;
  text-decoration: none;
  border-bottom: 2px solid transparent;
}
.main-layout__tab--active a {
  color: #1e293b;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}
.main-layout__content {
  padding: 1.5rem;
}
</style>
