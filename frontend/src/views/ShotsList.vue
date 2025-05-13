<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, ref } from 'vue'

const shots = ref([])
const loading = ref(true)
const error = ref(null)

const fetchShots = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await axios.get('/api/shots/')
    shots.value = response.data.results
  } catch (err) {
    error.value = err.response?.data?.detail || 'Произошла ошибка при загрузке шотов'
    console.error('Ошибка при загрузке шотов:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchShots()
})
</script>

<template>
  <div class="shots-list">
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    <div v-else-if="loading" class="loading">Загрузка...</div>
    <div v-else class="shots-grid">
      <div v-for="shot in shots" :key="shot.url" class="shot-card">
        <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" class="shot-image" />
        <div v-else class="shot-no-thumb">Нет превью</div>
        <div class="shot-info">
          {{ shot.name }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
