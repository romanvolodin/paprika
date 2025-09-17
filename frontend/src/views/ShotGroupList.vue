<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode

const _shotGroups = ref([])
const _loaded = ref(false)
const _error = ref(null)

document.title = `${projectCode}: Группы`

async function fetchShotGroups() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shot-groups/`)
    _shotGroups.value = response.data
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  } finally {
    _loaded.value = true
  }
}

onMounted(async () => {
  await fetchShotGroups()
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="tasks-list">
    <div v-if="_shotGroups.length === 0" class="empty">Групп шотов пока нет</div>

    <div v-else>
      <div v-for="shotGroup in _shotGroups" :key="shotGroup.id">
        <router-link
          :to="{ name: 'shot-group-details-by-project', params: { shotGroupId: shotGroup.id } }"
        >
          {{ shotGroup.name }}
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

.tasks-list {
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
</style>
