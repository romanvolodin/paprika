<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    required: true
  },
  statuses: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)

const selectedStatus = computed(() => {
  return props.statuses.find(status => status.id === props.modelValue) || props.statuses[0]
})

const selectedStatusTitle = computed(() => {
  return selectedStatus.value ? selectedStatus.value.title : 'Выберите статус'
})

const selectedStatusColor = computed(() => {
  return selectedStatus.value ? selectedStatus.value.color : '#ccc'
})

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const selectStatus = (status) => {
  emit('update:modelValue', status.id)
  isOpen.value = false
}

document.addEventListener('click', (event) => {
  if (!event.target.closest('.status-dropdown')) {
    isOpen.value = false
  }
})
</script>

<template>
  <div class="status-dropdown" :class="{ open: isOpen }">
    <div class="selected-status" @click="toggleDropdown" :style="{ backgroundColor: selectedStatusColor }">
      <span class="status-text">{{ selectedStatusTitle }}</span>
      <span class="arrow" :class="{ rotated: isOpen }">▼</span>
    </div>
    <div class="dropdown-list" v-show="isOpen">
      <div
        v-for="status in statuses"
        :key="status.id"
        class="dropdown-item"
        @click="selectStatus(status)"
        :style="{ backgroundColor: status.color }"
      >
        {{ status.title }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-dropdown {
  position: relative;
  width: 200px;
}

.selected-status {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.selected-status:hover {
  opacity: 0.9;
}

.arrow.rotated {
  transform: rotate(180deg);
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  border-radius: 4px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  margin-top: 5px;
  z-index: 1000;
  max-height: 240px;
}

.dropdown-item {
  padding: 5px 7px;
  cursor: pointer;
  color: white;
  filter: brightness(0.7);
}

.dropdown-item:hover {
  filter: brightness(1);
}
</style>
