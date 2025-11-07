<script setup>
import ShotCard from '@/components/ShotCard.vue'
import axios from '@/config/axiosConfig'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode

const _groups = ref([])
const _loaded = ref(false)
const _error = ref(null)
const _selectedStatuses = ref([])
const _isStatusFilterInverted = ref(false)
const _addTaskPanel = ref(null)

document.title = `${projectCode}: Шоты`

const shot_status_colors = {
  'Нет задач': '#CCCCCC',
  'Не начат': '#D40000',
  'В работе': '#FFAA00',
  Готов: '#009900',
  'Есть комментарий': '#FF6600',
  Принят: '#0088CC',
  Отдан: '#7700BE',
  Отмена: '#999999',
  'На паузе': '#3D3D3D',
}

async function fetchShots() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shots2/`)
    _groups.value = response.data
    console.log(response.data)
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  } finally {
    _loaded.value = true
  }
}

onMounted(async () => {
  await fetchShots()
})

const statuses = computed(() => {
  console.log(typeof _groups.value, Array.isArray(_groups.value), _groups.value)
  return [...new Set(_groups.value.flatMap((ep) => ep.shots.map((shot) => shot.status)))]
})

const filteredGroups = computed(() => {
  if (_selectedStatuses.value.length === 0) return _groups.value

  const filteredData = _groups.value
    .map((group) => {
      const filteredShots = group.shots.filter((shot) => {
        const hasAllowedStatus = _selectedStatuses.value.includes(shot.status)
        return _isStatusFilterInverted.value ? !hasAllowedStatus : hasAllowedStatus
      })

      return {
        ...group,
        shots: filteredShots,
      }
    })
    .filter((group) => group.shots.length > 0)

  return filteredData
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="shots-list">
    <div v-if="_groups.length === 0" class="empty">Шотов пока нет</div>

    <div v-else class="shots-area">
      <div v-for="grp in filteredGroups" :key="grp.url">
        <h2>{{ grp.name }}</h2>
        <div class="shots-grid">
        <ShotCard
          v-for="shot in grp.shots"
          :key="shot.url"
          :project-code="projectCode"
          :name="shot.name"
          :status="shot.status"
          :status-color="shot_status_colors[shot.status]"
          :thumb="shot.thumb"
        />
        </div>
      </div>
    </div>

    <aside class="filter-panel">
      <div v-if="_loaded && !_error">
        <h3>Статус</h3>

        <p style="margin-bottom: 10px">
          <label>
            <input type="checkbox" v-model="_isStatusFilterInverted" />
            Инвертировать фильтр
          </label>
        </p>

        <p v-for="status in statuses" :key="status">
          <label>
            <input type="checkbox" :value="status" v-model="_selectedStatuses" />
            <span
              class="shot-status-filter"
              :style="{ 'background-color': shot_status_colors[status] }"
              >{{ status }}</span
            >
          </label>
        </p>
      </div>
    </aside>
  </div>

  <dialog ref="_addTaskPanel">
    <header>
      <h2>Добавить задачи</h2>
      <button @click="_addTaskPanel.close()">𐄂</button>
    </header>

    <div class="dialog-content">...</div>

    <footer>
      <button>Добавить задачи</button>
    </footer>
  </dialog>
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
.shots-header {
  display: flex;
  align-items: end;
  gap: 30px;
}

.shots-list {
  display: flex;
  padding: 1rem;
}

.shots-area {
  flex-grow: 1;
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

.shot-card-selected {
  border: 3px solid #ff00ff;
}

.shot-card:hover {
  transform: translateY(-4px);
}
.shot-checkbox {
  position: absolute;
  z-index: 1;
  padding: 10px;
  padding-left: 13px;
  width: 80px;
  height: 80px;
}
.shot-checkbox > input[type='checkbox'] {
  display: none;
}
.shot-checkbox > input[type='checkbox']:checked,
.shot-checkbox:hover > input[type='checkbox'] {
  display: block;
}

.shot-status-filter {
  margin: 5px;
  border-radius: 5px;
  padding: 2px 7px;
  color: #fff;
  font-size: 12px;
}

table {
  border-collapse: collapse;
  width: 100%;
}
th,
td {
  border: 1px solid #ccc;
  padding: 8px;
}

.filter-panel {
  flex-shrink: 1;
  padding: 20px;
  max-width: 300px;
}
dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: none;
  padding: 10px;
  width: 700px;
}
dialog > header {
  display: flex;
  justify-content: space-between;
}
dialog > header > button {
  padding: 10px;
}
dialog > footer {
  display: flex;
  justify-content: end;
}
dialog > footer > button {
  padding: 10px;
}
</style>
