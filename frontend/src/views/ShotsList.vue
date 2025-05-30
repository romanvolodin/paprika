<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from '@/config/axiosConfig'

const route = useRoute()
const projectCode = route.params.projectCode

const _shots = ref([])
const _loaded = ref(false)
const _error = ref(null)

async function fetchShots() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shots/`)
    _shots.value = response.data
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  } finally {
    _loaded.value = true
  }
}

onMounted(async () => {
  await fetchShots()
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="shots-list">
    <div v-if="_shots.length === 0" class="empty">Шотов пока нет</div>

    <div v-else class="shots-grid">
      <div v-for="shot in _shots" :key="shot.url" class="shot-card">
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
* {
  text-decoration: none;
}
.empty-message {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 90vh;
}

.shots-list {
  padding: 1rem;
}

.error-message {
  margin: 1rem 0;
  border: 1px solid #dc3545;
  border-radius: 4px;
  background-color: #f8d7da;
  padding: 1rem;
  color: #dc3545;
}

.loading {
  padding: 2rem;
  color: #666;
  font-size: 1.2rem;
  text-align: center;
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
