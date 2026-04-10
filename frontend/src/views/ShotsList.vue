<script setup>
import axios from '@/config/axiosConfig'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community'
import { AgGridVue } from 'ag-grid-vue3'

import AG_GRID_LOCALE_RU from '@/config/agGridLocaleRu'

ModuleRegistry.registerModules([AllCommunityModule])

const router = useRouter()
const route = useRoute()
const projectCode = route.params.projectCode

const _shots = ref([])
const _loaded = ref(false)
const _error = ref(null)
const _mode = ref('grid')
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

const imageLinkCellRenderer = (params) => {
  const link = document.createElement('a')
  link.href = router.resolve({
    name: 'shot-details',
    params: { projectCode: projectCode, shotName: params.data.name },
  }).href
  link.style.display = 'block'
  link.style.height = '100%'
  link.style.width = '100%'
  link.style.textDecoration = 'none'

  const img = document.createElement('img')
  img.src = params.value
  img.style.height = '100%'
  img.style.width = 'auto'
  img.style.objectFit = 'cover'

  link.appendChild(img)

  link.addEventListener('click', (e) => {
    e.preventDefault()
    router.push({
      name: 'shot-details',
      params: { projectCode: projectCode, shotName: params.data.name },
    })
  })

  return link
}

const _ag_colDefs = ref([
  { cellRenderer: imageLinkCellRenderer, field: 'thumb', width: 390 },
  { headerName: 'Имя', field: 'name', filter: true },
  { headerName: 'Статус', field: 'status', filter: true },
  { field: 'rec_timecode', filter: true },
  { field: 'group', filter: true },
  { field: 'task', filter: true },
  { field: 'created_at', filter: true },
])

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

const statuses = computed(() => {
  return [...new Set(_shots.value.map((shot) => shot.status))]
})

const filteredShots = computed(() => {
  if (_selectedStatuses.value.length === 0) return _shots.value

  return _shots.value.filter((task) => {
    const matches = _selectedStatuses.value.includes(task.status)
    return _isStatusFilterInverted.value ? !matches : matches
  })
})

const selectedShots = computed(() => {
  return _shots.value.filter((shot) => {
    return shot.is_selected === true
  })
})

function toggleShotSelection(shot) {
  shot.is_selected = !shot.is_selected
}

function handleKeyDown(event) {
  if (event.code === 'KeyT') {
    if (_addTaskPanel.value && !_addTaskPanel.value.open) {
      _addTaskPanel.value.showModal()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <header class="shots-header">
    <h1 v-if="filteredShots">
      Шоты
      <sub>({{ filteredShots.length }})</sub>
    </h1>
    <div v-if="selectedShots.length > 0">Выделено: {{ selectedShots.length }}</div>
  </header>

  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="shots-list">
    <div v-if="_shots.length === 0" class="empty-state">
      <div class="empty-state-illustration">
        <svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
      </div>
      <h2 class="empty-state-title">Здесь буду шоты</h2>
      <p class="empty-state-description">
        В этом проекте пока нет ни одного шота. Вы можете создать шоты несколькими способами:
      </p>
      <div class="empty-state-actions">
        <router-link :to="{ name: 'create-shots', params: { projectCode } }" class="btn btn-primary">
          Создать один шот
        </router-link>
        <router-link :to="{ name: 'create-shots', params: { projectCode } }" class="btn btn-secondary">
          Создать список шотов
        </router-link>
        <router-link :to="{ name: 'upload-version', params: { projectCode, shotName: 'dummy' } }" class="btn btn-outline">
          Загрузить таблицу (XLSX, ODS)
        </router-link>
      </div>
    </div>

    <template v-else>
      <div class="shots-area">
        <div>
          <button @click="_mode = 'list'">Список</button>
          <button @click="_mode = 'grid'">Сетка</button>
        </div>
        <div v-if="_mode === 'grid'" class="shots-grid">
          <div
            v-for="shot in filteredShots"
            :key="shot.url"
            class="shot-card"
            :class="{ 'shot-card-selected': shot.is_selected }"
            @click.alt="toggleShotSelection(shot)"
          >
            <label class="shot-checkbox">
              <input type="checkbox" v-model="shot.is_selected" />
            </label>

            <router-link
              :to="{
                name: 'shot-details',
                params: { projectCode: projectCode, shotName: shot.name },
              }"
            >
              <span
                class="shot-status"
                :style="{ 'background-color': shot_status_colors[shot.status] }"
                >{{ shot.status }}</span
              >

              <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" class="shot-image" />
              <div v-else class="shot-no-thumb">Нет превью</div>
              <div class="shot-info">
                {{ shot.name }}
              </div>
            </router-link>
          </div>
        </div>

        <div v-else-if="_mode === 'list'">
          <ag-grid-vue
            :rowData="_shots"
            :columnDefs="_ag_colDefs"
            :localeText="AG_GRID_LOCALE_RU"
            :rowHeight="150"
            style="height: 800px"
          >
          </ag-grid-vue>
        </div>
      </div>

      <aside class="filter-panel">
        <div>
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
    </template>
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

.shot-card {
  position: relative;
  transition: transform 0.1s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
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
.shot-status {
  position: absolute;
  right: 0;
  margin: 5px;
  border-radius: 5px;
  padding: 2px 7px;
  color: #fff;
  font-size: 12px;
}

.shot-status-filter {
  margin: 5px;
  border-radius: 5px;
  padding: 2px 7px;
  color: #fff;
  font-size: 12px;
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
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 3rem 1rem;
  max-width: 700px;
  margin: 0 auto;
}
.empty-state-illustration {
  margin-bottom: 1.5rem;
  color: #6c757d;
}
.empty-state-illustration svg {
  stroke: #adb5bd;
}
.empty-state-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: #343a40;
}
.empty-state-description {
  font-size: 1.1rem;
  color: #6c757d;
  margin-bottom: 2rem;
  max-width: 600px;
  line-height: 1.5;
}
.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 2rem;
}
.empty-state-actions .btn {
  padding: 0.75rem 1.5rem;
  border-radius: 0.375rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s;
  display: inline-block;
}
.empty-state-actions .btn-primary {
  background-color: #0d6efd;
  color: white;
  border: 1px solid #0d6efd;
}
.empty-state-actions .btn-primary:hover {
  background-color: #0b5ed7;
  border-color: #0a58ca;
}
.empty-state-actions .btn-secondary {
  background-color: #6c757d;
  color: white;
  border: 1px solid #6c757d;
}
.empty-state-actions .btn-secondary:hover {
  background-color: #5c636a;
  border-color: #565e64;
}
.empty-state-actions .btn-outline {
  background-color: transparent;
  color: #0d6efd;
  border: 1px solid #0d6efd;
}
.empty-state-actions .btn-outline:hover {
  background-color: #0d6efd;
  color: white;
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
