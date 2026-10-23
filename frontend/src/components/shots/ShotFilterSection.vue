<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NCheckbox, NTag } from 'naive-ui'
import { tagColor } from '@/utils/color'

type Value = number | 'none'

export interface ShotFilterOption {
  value: Value
  label: string
  color?: string
}

const props = defineProps<{
  title: string
  options: ShotFilterOption[]
  selected: Value[]
  inverted: boolean
}>()

const emit = defineEmits<{
  change: [selected: Value[], inverted: boolean]
}>()

const isActive = computed(() => props.selected.length > 0)

function toggle(value: Value, checked: boolean) {
  const selected = checked
    ? [...props.selected, value]
    : props.selected.filter((candidate) => candidate !== value)
  emit('change', selected, props.inverted)
}
</script>

<template>
  <section class="filter-section">
    <div class="filter-section__heading">
      <h3 class="filter-section__title">{{ title }}</h3>
      <n-button v-if="isActive" size="tiny" quaternary @click="emit('change', [], false)">
        Сбросить
      </n-button>
    </div>

    <n-checkbox
      class="filter-section__invert"
      size="small"
      :checked="inverted"
      :disabled="!isActive"
      @update:checked="emit('change', selected, $event)"
    >
      Инвертировать фильтр
    </n-checkbox>

    <ul class="filter-section__options">
      <li v-for="option in options" :key="option.value">
        <n-checkbox
          size="small"
          :checked="selected.includes(option.value)"
          @update:checked="toggle(option.value, $event)"
        >
          <n-tag
            v-if="option.color"
            size="small"
            round
            :bordered="true"
            :color="tagColor(option.color)"
          >
            {{ option.label }}
          </n-tag>
          <template v-else>{{ option.label }}</template>
        </n-checkbox>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.filter-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-section__heading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 24px;
}

.filter-section__title {
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0;
}

.filter-section__options {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}
</style>
