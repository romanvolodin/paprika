<script setup>
import ShotCard from '@/components/ShotCard.vue'
import axios from '@/config/axiosConfig'
import { previousRoute } from '@/router'
import { computed, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode

const _groups = ref([])
const _loaded = ref(false)
const _error = ref(null)
const _selectedStatuses = ref([])
const _isStatusFilterInverted = ref(false)
const _selectedAssignees = ref([])
const _isAssigneeFilterInverted = ref(false)

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
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  } finally {
    _loaded.value = true
  }
}

onMounted(async () => {
  await fetchShots()

  const savedScrollPosition = localStorage.getItem(`scrollPosition-${route.path}`)
  if (savedScrollPosition && previousRoute.value.fullPath !== '/') {
    setTimeout(() => {
      window.scrollTo(0, parseInt(savedScrollPosition))
    }, 0)
  }
})

onBeforeRouteLeave(() => {
  localStorage.setItem(`scrollPosition-${route.path}`, window.scrollY.toString())
})

const statuses = computed(() => {
  return [...new Set(_groups.value.flatMap((ep) => ep.shots.map((shot) => shot.status)))]
})

const assignees = computed(() => {
  const allAssignees = _groups.value.flatMap((ep) =>
    ep.shots.flatMap((shot) => shot.assignees || [])
  )
  const seen = new Map()
  allAssignees.forEach((a) => {
    if (!seen.has(a.id)) {
      seen.set(a.id, a)
    }
  })
  const list = Array.from(seen.values()).sort((a, b) => a.name.localeCompare(b.name))
  list.unshift({ id: -1, name: 'Не назначен' })
  return list
})

const filteredGroups = computed(() => {
  // Фильтрация по статусу
  const filterByStatus = (shot) => {
    if (_selectedStatuses.value.length === 0) return true
    const hasAllowedStatus = _selectedStatuses.value.includes(shot.status)
    return _isStatusFilterInverted.value ? !hasAllowedStatus : hasAllowedStatus
  }

  // Фильтрация по исполнителю
  const filterByAssignee = (shot) => {
    if (_selectedAssignees.value.length === 0) return true
    const shotAssignees = shot.assignees || []
    const hasAllowedAssignee = _selectedAssignees.value.some((id) => {
      if (id === -1) {
        return shotAssignees.length === 0
      } else {
        return shotAssignees.some(a => a.id === id)
      }
    })
    return _isAssigneeFilterInverted.value ? !hasAllowedAssignee : hasAllowedAssignee
  }

  const filteredData = _groups.value
    .map((group) => {
      const filteredShots = group.shots.filter((shot) => {
        return filterByStatus(shot) && filterByAssignee(shot)
      })

      filteredShots.sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }),
      )

      return {
        ...group,
        shots: filteredShots,
      }
    })
    .filter((group) => group.shots.length > 0)
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }))

  return filteredData
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="shots-list">
    <div v-if="_groups.length === 0" class="empty-state">
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
        <router-link :to="{ name: 'create-shot', params: { projectCode } }" class="btn btn-primary">
          Создать шот
        </router-link>
        <router-link :to="{ name: 'create-shots-from-list', params: { projectCode } }" class="btn btn-secondary">
          Создать шоты из списка
        </router-link>
        <router-link :to="{ name: 'create-shots-from-table', params: { projectCode } }" class="btn btn-outline">
          Загрузить из таблицы (XLSX, ODS)
        </router-link>
      </div>
    </div>

    <template v-else>
      <div class="shots-area">
        <div class="header">
          <h1>Шоты</h1>
          <router-link
            :to="{ name: 'create-shots-from-list', params: { projectCode } }"
            class="btn btn-primary"
          >
            Создать шоты
          </router-link>
        </div>
        <div v-for="grp in filteredGroups" :key="grp.url">
          <h2 class="group-header">
            {{ grp.name }}
            <sub>({{ grp.shots.length }})</sub>
          </h2>
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

          <h3>Исполнитель</h3>

          <p style="margin-bottom: 10px">
            <label>
              <input type="checkbox" v-model="_isAssigneeFilterInverted" />
              Инвертировать фильтр
            </label>
          </p>

          <p v-for="assignee in assignees" :key="assignee.id">
            <label>
              <input type="checkbox" :value="assignee.id" v-model="_selectedAssignees" />
              <span class="shot-assignee-filter">{{ assignee.name }}</span>
            </label>
          </p>
         </div>
       </aside>
    </template>
  </div>
</template>

<style scoped>
* {
  text-decoration: none;
}
.group-header {
  font-size: 36px;
  margin-top: 50px;
  margin-bottom: 20px;
}

.shots-list {
  display: flex;
  padding: 1rem;
}

.shots-area {
  flex-grow: 1;
}

.shots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 5px;
}

.shot-status-filter {
  margin: 5px;
  border-radius: 5px;
  padding: 2px 7px;
  color: #fff;
  font-size: 12px;
}

.shot-assignee-filter {
  margin: 5px;
  padding: 2px 7px;
  font-size: 12px;
}

.filter-panel {
  flex-shrink: 1;
  padding: 20px;
  max-width: 300px;
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
</style>
