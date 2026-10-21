<script setup lang="ts">
import { NInputNumber, NSelect } from 'naive-ui'
import type { TaskDraft } from '@/composables/useShotTaskDrafts'
import type { ShotTaskOut } from '@/types/api'

defineProps<{
  rows: Array<{ item: ShotTaskOut; draft: TaskDraft }>
  statusOptions: Array<{ label: string; value: number }>
  loading: boolean
  loadFailed: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  status: [shotTaskId: number, statusId: number]
  hours: [shotTaskId: number, hours: number | null]
}>()
</script>

<template>
  <section class="upload-tasks">
    <h3 class="upload-tasks__heading">Задачи</h3>

    <p v-if="loadFailed" class="upload-tasks__note">Не удалось загрузить задачи.</p>
    <p v-else-if="!loading && rows.length === 0" class="upload-tasks__note">На кадре нет задач.</p>

    <ul v-else class="upload-tasks__list">
      <li v-for="{ item, draft } in rows" :key="item.id" class="upload-tasks__item">
        <div class="upload-tasks__title">
          <span class="mono upload-tasks__code">{{ item.task.code }}</span>
          <span>{{ item.task.name }}</span>
        </div>
        <div class="upload-tasks__controls">
          <n-select
            class="upload-tasks__status"
            size="small"
            :value="draft.status_id"
            :options="statusOptions"
            :disabled="disabled"
            @update:value="(value: number) => emit('status', item.id, value)"
          />
          <n-input-number
            class="upload-tasks__hours"
            size="small"
            :value="draft.actual_hours"
            :min="0"
            :precision="2"
            :show-button="false"
            :disabled="disabled"
            clearable
            placeholder="Часы"
            @update:value="(value: number | null) => emit('hours', item.id, value)"
          />
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.upload-tasks {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.upload-tasks__heading {
  margin: 0;
  font-size: var(--text-sm, 13px);
  font-weight: 600;
}

.upload-tasks__note {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.upload-tasks__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.upload-tasks__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.upload-tasks__title {
  display: flex;
  gap: var(--space-2);
  font-size: var(--text-sm, 13px);
}

.upload-tasks__code {
  color: var(--color-text-secondary);
}

.upload-tasks__controls {
  display: flex;
  gap: var(--space-2);
}

.upload-tasks__status {
  flex: 1;
  min-width: 0;
}

.upload-tasks__hours {
  width: 90px;
}
</style>
