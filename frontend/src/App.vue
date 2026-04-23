<template>
  <div
    data-test="app-root"
    class="harness-app"
  >
    <header class="harness-header">
      <h1>HarnessFlow</h1>
      <span
        class="pid-indicator"
        data-test="pid-indicator"
      >
        {{ activePid ?? '无活动项目' }}
      </span>
    </header>
    <main class="harness-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getActivePid } from '@/utils/pid';

const activePid = ref<string | null>(null);

onMounted(() => {
  activePid.value = getActivePid();
});
</script>

<style scoped>
.harness-app {
  font-family: system-ui, -apple-system, sans-serif;
  min-height: 100vh;
}
.harness-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: #1e293b;
  color: white;
}
.pid-indicator {
  font-size: 0.875rem;
  opacity: 0.85;
}
</style>
