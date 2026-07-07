<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'

import FeedUserBadge from '@/components/FeedUserBadge.vue'

const route = useRoute()
const projectCode = route.params.projectCode

const _items = ref([])
const _loaded = ref(false)
const _error = ref(null)

const monthNames = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

document.title = `${projectCode}: Лента событий`

function formatTime(isoString) {
  const d = new Date(isoString)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function formatDate(isoString) {
  const d = new Date(isoString)
  const day = d.getDate()
  const month = monthNames[d.getMonth()]
  const year = d.getFullYear()
  const currentYear = new Date().getFullYear()
  if (year === currentYear) {
    return `${day} ${month}`
  }
  return `${day} ${month} ${year}`
}

async function fetchFeed() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/feed/`)
    _items.value = response.data
  } catch (error) {
    _error.value = `${error.status}: ${error.response?.data?.detail || error.message}`
  } finally {
    _loaded.value = true
  }
}

onMounted(async () => {
  await fetchFeed()
})

// Группировка по дням
const groupedByDate = computed(() => {
  const groups = {}
  for (const item of _items.value) {
    const d = new Date(item.created_at)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    if (!groups[key]) {
      groups[key] = {
        dateLabel: formatDate(item.created_at),
        items: [],
      }
    }
    groups[key].items.push(item)
  }
  // Сортируем дни по убыванию
  const sortedKeys = Object.keys(groups).sort((a, b) => b.localeCompare(a))
  const result = sortedKeys.map((key) => groups[key])

  // КОСТЫЛЬ: если перед загрузкой версии идёт сообщение с разницей не больше 2 сек,
  // не выводим сообщение отдельно, а добавляем его текст к версии.
  // Нужно потому, что в БД нет прямой связи между версией и сообщением к ней.
  for (const day of result) {
    const merged = []
    for (let i = 0; i < day.items.length; i++) {
      const current = day.items[i]
      const next = day.items[i + 1]
      if (
        current.type === 'chat_message' &&
        next &&
        next.type === 'version' &&
        new Date(next.created_at) - new Date(current.created_at) <= 2000
      ) {
        next.data.message_text = current.data.text
        // сообщение не добавляем в merged, версию добавим на следующей итерации
      } else {
        merged.push(current)
      }
    }
    day.items = merged
  }

  return result
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="feed-page">
    <div class="feed-header">
      <h1>Лента событий</h1>
      <span class="project-badge">{{ projectCode }}</span>
    </div>

    <div v-if="_items.length === 0" class="empty-state">
      <div class="empty-state-illustration">
        <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
      </div>
      <p class="empty-state-text">В этом проекте пока нет событий</p>
    </div>

    <div v-else class="feed-list">
      <div v-for="day in groupedByDate" :key="day.dateLabel" class="feed-day">
        <div class="day-separator">
          <span class="day-label">{{ day.dateLabel }}</span>
        </div>

        <div
          v-for="item in day.items"
          :key="`${item.type}-${item.id}`"
          class="feed-item"
          :class="`feed-item--${item.type}`"
        >
          <span class="item-time">{{ formatTime(item.created_at) }}</span>

          <!-- Version uploaded -->
          <template v-if="item.type === 'version'">
            <FeedUserBadge :user="item.created_by" />
            <span class="item-action">загрузил версию</span>
            <router-link
              class="item-shot-link"
              :to="{ name: 'shot-details', params: { projectCode, shotName: item.data.shot_name } }"
            >{{ item.data.name }}</router-link>
            <span v-if="item.data.message_text" class="item-message-text">{{ item.data.message_text }}</span>
          </template>

          <!-- Task created -->
          <template v-else-if="item.type === 'task'">
            <FeedUserBadge :user="item.created_by" />
            <span class="item-action">создал задачу</span>
            <span class="item-description">{{ item.data.description }}</span>
          </template>

          <!-- Chat message -->
          <template v-else-if="item.type === 'chat_message'">
            <FeedUserBadge :user="item.created_by" />
            <span class="item-action">написал в чате</span>
            <router-link
              class="item-shot-link"
              :to="{ name: 'shot-details', params: { projectCode, shotName: item.data.shot_name } }"
            >{{ item.data.shot_name }}</router-link>
            <span class="item-message-text">{{ item.data.text }}</span>
          </template>

          <!-- Unknown type -->
          <template v-else>
            <span class="item-unknown">Неизвестное событие ({{ item.type }})</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feed-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 1.5rem 1rem;
}

.feed-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.feed-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.project-badge {
  font-size: 0.75rem;
  font-weight: 600;
  background-color: #007bff;
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
}

/* Day separator */
.feed-day {
  margin-bottom: 1.5rem;
}

.day-separator {
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
}

.day-separator::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: #4a4a4a;
  margin-left: 0.75rem;
}

.day-label {
  font-weight: 600;
  color: #6c757d;
  letter-spacing: 0.05em;
}

/* Feed item */
.feed-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0;
  border-radius: 6px;
  transition: background-color 0.15s;
  font-size: 0.9rem;
  line-height: 1.4;
}

.feed-item:hover {
  background-color: rgba(0, 0, 0, 0.03);
}

.item-time {
  font-size: 0.8rem;
  font-weight: 500;
  color: #6c757d;
  white-space: nowrap;
  min-width: 3.5rem;
  font-variant-numeric: tabular-nums;
}

.item-user {
  font-weight: 600;
  /* color: #212529; */
  white-space: nowrap;
}

.item-action {
  color: #6c757d;
  white-space: nowrap;
}

.item-shot-link {
  color: #007bff;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
}

.item-shot-link::after {
  content: ":";
  color: #6c757d;
  text-decoration: none;
}

.item-shot-link:hover {
  text-decoration: underline;
}

.item-description {
  font-style: italic;
}

.item-message-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-unknown {
  color: #dc3545;
  font-style: italic;
}

/* States */
.empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 50vh;
  color: #6c757d;
  font-size: 1.1rem;
}

.error {
  margin: 1rem;
  padding: 1rem;
  border: 1px solid #dc3545;
  border-radius: 4px;
  background-color: #f8d7da;
  color: #dc3545;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
}

.empty-state-illustration {
  margin-bottom: 1rem;
  color: #adb5bd;
}

.empty-state-text {
  font-size: 1.1rem;
  color: #6c757d;
}
</style>
