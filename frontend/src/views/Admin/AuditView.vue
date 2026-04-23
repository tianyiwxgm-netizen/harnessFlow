<template>
  <section
    :data-test="`admin-subtab-view-${subtabId}`"
    class="admin-subtab-view"
  >
    <h4>{{ title }}</h4>
    <p class="admin-subtab-view__hint">
      (L2-07 {{ subtabId }} 占位 · 审计链查询经 IC-18 由 WP09 接入 L1-09)
    </p>
  </section>
</template>

<script setup lang="ts">
import { ADMIN_SUBTAB_REGISTRY } from '@/domain/admin_subtabs';
const subtabId = 'audit' as const;
const title = ADMIN_SUBTAB_REGISTRY[subtabId].title;
</script>

<style scoped>
.admin-subtab-view { padding: 0.5rem 0; }
.admin-subtab-view__hint { color: #94a3b8; font-size: 0.75rem; }
</style>
