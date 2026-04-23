<template>
  <section
    :data-test="`tab-view-${tabId}`"
    class="tab-view"
  >
    <h2>{{ title }}</h2>
    <p class="tab-view__pid">
      <span
        v-if="uiSession.hasActiveProject"
        data-test="tab-view-pid"
      >当前项目: {{ uiSession.activeProjectId }}</span>
      <span
        v-else
        data-test="tab-view-no-pid"
      >无活动项目</span>
    </p>
    <p class="tab-view__hint">
      (L1-10 L2-01 占位)
    </p>
  </section>
</template>

<script setup lang="ts">
import { useUISessionStore } from '@/stores/ui_session';
import { TAB_REGISTRY } from '@/domain/tabs';

const tabId = 'artifacts' as const;
const title = TAB_REGISTRY[tabId].title;
const uiSession = useUISessionStore();
</script>

<style scoped>
.tab-view { padding: 1rem; background: white; border: 1px solid #e2e8f0; border-radius: 6px; }
.tab-view__pid { color: #475569; font-size: 0.875rem; }
.tab-view__hint { color: #94a3b8; font-size: 0.75rem; }
</style>
