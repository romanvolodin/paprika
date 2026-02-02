<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Handsontable from 'handsontable'
import 'handsontable/styles/handsontable.css'
import 'handsontable/styles/ht-theme-classic.css'

const router = useRouter()
const route = useRoute()
const projectCode = route.params.projectCode

const tableContainer = ref(null)
let hotInstance = null
const shotGroups = ref([])
const tasks = ref([])

const _error = ref(null)
const _success = ref(false)
const _loading = ref(false)

async function fetchShotGroups() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shot-groups/`)
    shotGroups.value = response.data.map((group) => group.name)
  } catch (error) {
    console.error('Ошибка при загрузке групп шотов:', error)
  }
}

async function fetchTasks() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/tasks/`)
    tasks.value = response.data.map((task) => task.description)
  } catch (error) {
    console.error('Ошибка при загрузке задач:', error)
  }
}

const data = [
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
]

const colHeaders = Object.keys(data[0])

onMounted(async () => {
  if (!tableContainer.value) return

  await fetchShotGroups()
  await fetchTasks()

  hotInstance = new Handsontable(tableContainer.value, {
    data,
    themeName: "ht-theme-classic-dark-auto",
    colHeaders,
    rowHeaders: true,
    height: 'auto',
    licenseKey: 'non-commercial-and-evaluation',
    manualRowMove: true,
    manualColumnMove: true,
    contextMenu: true,
    stretchH: 'all',
    autoInsertRow: true,
    columns: [
      { data: 'name', type: 'text' },
      { data: 'rec_timecode', type: 'text' },
      {
        data: 'group',
        type: 'dropdown',
        source: shotGroups.value,
        strict: false,
      },
      {
        data: 'task',
        type: 'dropdown',
        source: tasks.value,
        strict: false,
      },
    ],
  })
})

onUnmounted(() => {
  if (hotInstance) {
    hotInstance.destroy()
  }
})

async function submitNewShots() {
  // Reset messages
  _error.value = null
  _success.value = false
  _loading.value = true

  try {
    const newShots = hotInstance
      .getSourceData()
      .filter((shot) => shot.name || shot.rec_timecode || shot.group || shot.task)
    console.log(newShots)

    if (newShots.length === 0) {
      throw new Error('Нет объектов для отправки')
    }
    await axios.post(`/api/projects/${projectCode}/shots/create`, newShots)

    _success.value = true

    setTimeout(() => {
      router.push({name: 'shots-by-project', params: {projectCode}})
    }, 1500)
  } catch (error) {
    if (error.message === 'Нет объектов для отправки') {
      _error.value = error.message
    } else if (error.response?.data?.errors) {
      const errors = error.response.data.errors
      let errorMessages = []

      for (const [index, errorObj] of errors.entries()) {
        if (typeof errorObj === 'string') {
          errorMessages.push(`Общая ошибка: ${errorObj}`)
        } else if (typeof errorObj === 'object' && errorObj !== null) {
          for (const [field, messages] of Object.entries(errorObj)) {
            if (Array.isArray(messages)) {
              errorMessages.push(`Строка ${index + 1}, поле "${field}": ${messages.join(', ')}`)
            } else {
              errorMessages.push(`Строка ${index + 1}, поле "${field}": ${messages}`)
            }
          }
        }
      }

      _error.value = errorMessages.join('; ')
    } else if (error.response?.data) {
      if (Array.isArray(error.response.data)) {
        _error.value = error.response.data.join(', ')
      } else if (typeof error.response.data === 'object') {
        _error.value = JSON.stringify(error.response.data)
      } else {
        _error.value = error.response.data.toString()
      }
    } else if (error.request) {
      _error.value = 'Ошибка сети. Проверьте подключение к серверу.'
    } else {
      _error.value = 'Произошла ошибка при создании шотов'
    }

    console.error('Ошибка:', error)
  } finally {
    _loading.value = false
  }
}
</script>

<template>
  <div ref="tableContainer" style="width: 100%; margin: 20px auto"></div>

  <div v-if="_error" class="error-message">
    {{ _error }}
  </div>

  <div v-if="_success" class="success-message">
    Шоты успешно созданы! Перенаправление...
  </div>

  <div v-if="_loading" class="loading-indicator">
    Создание шотов...
  </div>

  <button @click="submitNewShots" :disabled="_loading || _success">Отправить</button>
</template>

<style scoped>
.error-message {
  margin: 20px 0;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  background-color: #f8d7da;
  padding: 12px;
  color: #721c24;
}

.success-message {
  margin: 20px 0;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  background-color: #d4edda;
  padding: 12px;
  color: #155724;
}

.loading-indicator {
  margin: 20px 0;
  text-align: center;
  font-style: italic;
}
</style>
