<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const options = [
  { value: 'chat_message', label: 'Сообщения' },
  { value: 'version', label: 'Версии' },
  { value: 'task', label: 'Задачи' },
]

const open = ref(false)
const containerRef = ref(null)

const selected = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const noneSelected = computed(() => selected.value.length === 0)
const allSelected = computed(() => options.every((o) => selected.value.includes(o.value)))
const isActive = computed(() => !noneSelected.value && !allSelected.value)

const buttonLabel = computed(() => {
  if (noneSelected.value || allSelected.value) {
    return 'Все события'
  }
  if (selected.value.length === 1) {
    const opt = options.find((o) => o.value === selected.value[0])
    return opt ? opt.label : selected.value[0]
  }
  return `${selected.value.length} события`
})

function toggleOption(value) {
  if (selected.value.includes(value)) {
    const next = selected.value.filter((v) => v !== value)
    selected.value = next
  } else {
    selected.value = [...selected.value, value]
  }
}

function onClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<template>
  <div ref="containerRef" class="type-filter">
    <button class="type-filter-btn" :class="{ active: isActive }" @click="open = !open" type="button">
      {{ buttonLabel }}
      <svg
        class="type-filter-chevron"
        :class="{ rotated: open }"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
      >
        <path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <div v-if="open" class="type-filter-dropdown">
      <label
        v-for="opt in options"
        :key="opt.value"
        class="type-filter-option"
      >
        <input
          type="checkbox"
          :checked="selected.includes(opt.value)"
          @change="toggleOption(opt.value)"
        />
        <span>{{ opt.label }}</span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.type-filter {
  position: relative;
  outline: none;
}

.type-filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  font-size: 0.8rem;
  font-weight: 500;
  border: 1px solid #6c757d;
  border-radius: 6px;
  background: transparent;
  color: #6c757d;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
  white-space: nowrap;
}

.type-filter-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.type-filter-btn.active {
  border-color: #007bff;
  color: #007bff;
  background-color: rgba(0, 123, 255, 0.06);
}

.type-filter-chevron {
  transition: transform 0.2s;
}

.type-filter-chevron.rotated {
  transform: rotate(180deg);
}

.type-filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 170px;
  background: #fff;
  border: 1px solid #ced4da;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 6px 0;
  z-index: 100;
}

.type-filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: 0.85rem;
  color: #212529;
  cursor: pointer;
  transition: background-color 0.12s;
}

.type-filter-option:hover {
  background-color: #f1f3f5;
}

.type-filter-option input[type="checkbox"] {
  margin: 0;
  accent-color: #007bff;
}

.type-filter-option--all {
  border-bottom: 1px solid #e9ecef;
  margin-bottom: 2px;
  padding-bottom: 8px;
}
</style>
