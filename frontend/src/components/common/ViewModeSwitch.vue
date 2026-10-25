<script setup lang="ts">
import { NButton, NButtonGroup, NIcon } from 'naive-ui'
import { GridOutline, ListOutline } from '@vicons/ionicons5'
import type { ViewMode } from '@/composables/useViewMode'

defineProps<{ modelValue: ViewMode }>()

const emit = defineEmits<{ 'update:modelValue': [mode: ViewMode] }>()

const options = [
  { mode: 'table', label: 'Таблица', icon: ListOutline },
  { mode: 'cards', label: 'Карточки', icon: GridOutline },
] as const
</script>

<template>
  <n-button-group size="small" role="group" aria-label="Вид списка">
    <n-button
      v-for="option in options"
      :key="option.mode"
      :type="modelValue === option.mode ? 'primary' : 'default'"
      :secondary="modelValue === option.mode"
      :aria-pressed="modelValue === option.mode"
      :aria-label="option.label"
      :title="option.label"
      @click="emit('update:modelValue', option.mode)"
    >
      <template #icon><n-icon :component="option.icon" /></template>
    </n-button>
  </n-button-group>
</template>
