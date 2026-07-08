<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

defineProps({
  modelValue: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const containerRef = ref(null)

function select(value) {
  emit('update:modelValue', value)
  open.value = false
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
  <div ref="containerRef" class="my-filter">
    <button class="my-filter-btn" :class="{ active: modelValue }" @click="open = !open" type="button">
      {{ modelValue ? 'По моим кадрам' : 'По всему проекту' }}
      <svg
        class="my-filter-chevron"
        :class="{ rotated: open }"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
      >
        <path d="M3 5L6 8L9 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <div v-if="open" class="my-filter-dropdown">
      <label
        class="my-filter-option"
        :class="{ active: !modelValue }"
      >
        <input
          type="radio"
          name="myFilter"
          :checked="!modelValue"
          @change="select(false)"
        />
        <span>По всему проекту</span>
      </label>
      <label
        class="my-filter-option"
        :class="{ active: modelValue }"
      >
        <input
          type="radio"
          name="myFilter"
          :checked="modelValue"
          @change="select(true)"
        />
        <span>По моим кадрам</span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.my-filter {
  position: relative;
  margin-left: auto;
  outline: none;
}

.my-filter-btn {
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

.my-filter-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.my-filter-btn.active {
  border-color: #007bff;
  color: #007bff;
  background-color: rgba(0, 123, 255, 0.06);
}

.my-filter-chevron {
  transition: transform 0.2s;
}

.my-filter-chevron.rotated {
  transform: rotate(180deg);
}

.my-filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 180px;
  background: #fff;
  border: 1px solid #ced4da;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 6px 0;
  z-index: 100;
}

.my-filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: 0.85rem;
  color: #212529;
  cursor: pointer;
  transition: background-color 0.12s;
}

.my-filter-option:hover {
  background-color: #f1f3f5;
}

.my-filter-option input[type="radio"] {
  margin: 0;
  accent-color: #007bff;
}
</style>
