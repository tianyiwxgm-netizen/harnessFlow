<template>
  <div
    data-test="admin-layout"
    class="admin-layout"
  >
    <h3 class="admin-layout__title">
      Admin · 管理后台
      <span
        v-if="!uiSession.isAdmin"
        class="admin-layout__warn"
        data-test="admin-not-authorized"
      >（当前无管理员权限）</span>
    </h3>
    <nav
      data-test="admin-layout-nav"
      class="admin-layout__nav"
    >
      <ul>
        <li
          v-for="sid in ADMIN_SUBTAB_IDS"
          :key="sid"
          :data-test="`admin-subtab-link-${sid}`"
          :class="{
            'admin-layout__subtab': true,
            'admin-layout__subtab--active': currentSubtabId === sid,
          }"
        >
          <RouterLink :to="ADMIN_SUBTAB_REGISTRY[sid].path">
            {{ ADMIN_SUBTAB_REGISTRY[sid].title }}
          </RouterLink>
        </li>
      </ul>
    </nav>
    <section
      class="admin-layout__content"
      data-test="admin-layout-content"
    >
      <router-view />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { ADMIN_SUBTAB_IDS, ADMIN_SUBTAB_REGISTRY } from '@/domain/admin_subtabs';
import { useUISessionStore } from '@/stores/ui_session';

const uiSession = useUISessionStore();
const route = useRoute();
const currentSubtabId = computed(() => (route.meta.adminSubtabId ?? null) as string | null);
</script>

<style scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.admin-layout__title {
  margin: 0;
  color: #1e293b;
}
.admin-layout__warn { color: #f97316; font-size: 0.875rem; margin-left: 0.5rem; }
.admin-layout__nav ul {
  display: flex;
  gap: 0.25rem;
  padding: 0;
  margin: 0;
  list-style: none;
  border-bottom: 1px solid #e2e8f0;
}
.admin-layout__subtab a {
  display: block;
  padding: 0.5rem 0.75rem;
  color: #64748b;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  font-size: 0.875rem;
}
.admin-layout__subtab--active a {
  color: #0f172a;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}
.admin-layout__content {
  padding: 1rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}
</style>
