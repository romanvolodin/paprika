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
    <div v-if="_groups.length === 0" class="empty">Шотов пока нет</div>

    <template v-else>
      <div class="shots-area">
        <div class="header">
          <h1>Шоты</h1>
          <router-link
            :to="{ name: 'create-shots', params: { projectCode } }"
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
</style>
