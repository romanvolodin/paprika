<script setup lang="ts" generic="T extends object">
import { NDataTable, NEmpty, NSpin, type DataTableColumns } from 'naive-ui'
import type { ViewMode } from '@/composables/useViewMode'

defineProps<{
  items: T[]
  columns: DataTableColumns<T>
  mode: ViewMode
  rowKey: (item: T) => string | number
  loading?: boolean
}>()

defineSlots<{ card(props: { item: T }): unknown }>()
</script>

<template>
  <n-data-table
    v-if="mode === 'table'"
    :columns="columns"
    :data="items"
    :loading="loading"
    :bordered="false"
    :row-key="rowKey"
  >
    <template #empty><n-empty description="Ничего не найдено" /></template>
  </n-data-table>

  <n-spin v-else :show="loading">
    <ul v-if="items.length > 0" class="item-list__cards">
      <li v-for="item in items" :key="rowKey(item)">
        <slot name="card" :item="item" />
      </li>
    </ul>
    <n-empty v-else-if="!loading" description="Ничего не найдено" class="item-list__empty" />
  </n-spin>
</template>

<style scoped>
.item-list__cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.item-list__empty {
  padding: var(--space-6, 32px) 0;
}
</style>
