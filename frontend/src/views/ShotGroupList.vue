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

  <div v-else class="groups-list">
    <div class="header">
      <h1>Группы шотов</h1>
      <router-link
        :to="{ name: 'create-shot-groups', params: { projectCode } }"
        class="btn btn-primary"
      >
        Создать группу
      </router-link>
    </div>

    <div v-if="_shotGroups.length === 0" class="empty">Групп шотов пока нет</div>

    <div v-else>
      <div v-for="shotGroup in _shotGroups" :key="shotGroup.id" class="group-item">
        <router-link
          :to="{ name: 'shot-group-details-by-project', params: { shotGroupId: shotGroup.id } }"
          class="group-link"
        >
          {{ shotGroup.name }}
          <span v-if="shotGroup.is_default" class="badge badge-default">По умолчанию</span>
          <span v-if="shotGroup.is_root" class="badge badge-root">Корневая</span>
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

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn {
  display: inline-block;
  transition: background-color 0.2s;
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  text-align: center;
  text-decoration: none;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.group-item {
  margin-bottom: 10px;
}

.group-link {
  display: inline-block;
  transition: background-color 0.2s;
  border-radius: 4px;
  background-color: var(--card-bg);
  padding: 10px 15px;
  color: var(--text-color);
  text-decoration: none;
}

.group-link:hover {
  background-color: #e9ecef;
}

.badge {
  margin-left: 10px;
  border-radius: 4px;
  padding: 2px 6px;
  font-weight: normal;
  font-size: 12px;
}

.badge-default {
  background-color: #28a745;
  color: white;
}

.badge-root {
  background-color: #17a2b8;
  color: white;
}
</style>
