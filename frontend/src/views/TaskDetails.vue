<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode
const taskId = route.params.taskId

const _task = ref(null)
const _loaded = ref(false)
const _error = ref(null)

onMounted(async () => {
  await fetchTask()
})

async function fetchTask() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/tasks/${taskId}`)
    _task.value = response.data
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
    _task.value = null
  } finally {
    _loaded.value = true
  }
}
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else>
    <h1>
      {{ _task.description }}
      <sub>({{ _task.shots.length }})</sub>
    </h1>

    <div class="shots-grid">
      <div v-for="shot in _task.shots" :key="shot.id" class="shot-card">
        <router-link
          :to="{
            name: 'shot-details',
            params: { projectCode: projectCode, shotName: shot.name },
          }"
        >
          <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" class="shot-image" />
          <div v-else class="shot-no-thumb">Нет превью</div>
          <div class="shot-info">
            {{ shot.name }}
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error {
  margin: 2rem;
  border: 1px solid #c41212;
  border-radius: 4px;
  background-color: #ffe6e6;
  padding: 1rem;
  color: #c41212;
  font-weight: bold;
}
.empty {
  display: flex;
  flex-grow: 1;
  justify-content: center;
  align-items: center;
}
.shots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 5px;
}
.shot-card {
  transition: transform 0.1s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.shot-card:hover {
  transform: translateY(-4px);
}

.shot-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.shot-no-thumb {
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #ddd;
  width: 100%;
  height: 200px;
  color: #999;
}

.shot-info {
  padding: 2px 5px;
}
</style>
