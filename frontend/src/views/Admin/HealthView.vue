<template>
  <section
    :data-test="`admin-subtab-view-${subtabId}`"
    class="admin-subtab-view"
  >
    <h4>{{ title }}</h4>
    <div
      v-if="state.loading"
      data-test="health-loading"
    >
      加载中...
    </div>
    <pre
      v-else-if="state.data"
      data-test="health-data"
      class="admin-subtab-view__json"
    >{{ JSON.stringify(state.data, null, 2) }}</pre>
    <p
      v-else-if="state.error"
      data-test="health-error"
      class="admin-subtab-view__error"
    >
      加载失败: {{ state.error }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue';
import { ADMIN_SUBTAB_REGISTRY } from '@/domain/admin_subtabs';
import { fetchAdminHealth, type AdminHealthResponse } from '@/api/admin';

const subtabId = 'health' as const;
const title = ADMIN_SUBTAB_REGISTRY[subtabId].title;

const state = reactive<{
  loading: boolean;
  data: AdminHealthResponse | null;
  error: string | null;
}>({ loading: true, data: null, error: null });

onMounted(async () => {
  try {
    state.data = await fetchAdminHealth();
  } catch (e) {
    state.error = e instanceof Error ? e.message : String(e);
  } finally {
    state.loading = false;
  }
});
</script>

<style scoped>
.admin-subtab-view { padding: 0.5rem 0; }
.admin-subtab-view__json {
  background: #f1f5f9; padding: 0.75rem; border-radius: 4px; font-size: 0.75rem;
}
.admin-subtab-view__error { color: #dc2626; }
</style>
