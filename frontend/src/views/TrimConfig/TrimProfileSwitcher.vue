<template>
  <div
    class="trim-switcher"
    data-test="trim-switcher"
  >
    <label
      for="trim-profile-select"
      class="trim-switcher__label"
    >裁剪档:</label>
    <select
      id="trim-profile-select"
      v-model="selected"
      class="trim-switcher__select"
      data-test="trim-switcher-select"
      @change="handleChange"
    >
      <option
        v-for="p in TRIM_PROFILES"
        :key="p"
        :value="p"
        :data-test="`trim-option-${p}`"
      >
        {{ displayLabel(p) }}
      </option>
    </select>
    <span
      v-if="store.lastSyncError"
      class="trim-switcher__err"
      data-test="trim-switcher-err"
    >
      同步失败: {{ store.lastSyncError }}
    </span>
    <span
      v-else-if="store.lastSyncedAt"
      class="trim-switcher__ok"
      data-test="trim-switcher-ok"
    >
      已同步
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useTrimProfileStore } from '@/stores/trim_profile';
import { TRIM_PROFILES, type TrimProfile } from '@/domain/trim_profile';
import { patchConfigProfile } from '@/api/trim_profile';

const store = useTrimProfileStore();
const selected = ref<TrimProfile>(store.current);

const DISPLAY: Record<TrimProfile, string> = {
  full: 'HEAVY · 完整',
  lean: 'STANDARD · 精简',
  custom: 'LIGHT · 自定义',
};

function displayLabel(p: TrimProfile): string {
  return DISPLAY[p];
}

async function handleChange() {
  const next = selected.value;
  store.switchProfile(next);
  try {
    await patchConfigProfile(next);
    store.markSyncSuccess();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    store.markSyncError(msg);
  }
}

// Keep local select in sync if store changes elsewhere (e.g. reset)
watch(
  () => store.current,
  (val) => {
    selected.value = val;
  },
);
</script>

<style scoped>
.trim-switcher {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
}
.trim-switcher__label {
  color: #cbd5e1;
}
.trim-switcher__select {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #475569;
  background: #0f172a;
  color: #f1f5f9;
}
.trim-switcher__err { color: #f87171; }
.trim-switcher__ok { color: #4ade80; }
</style>
