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

const _error = ref(null)
const _success = ref(false)
const _loading = ref(false)

const data = [
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
  { name: '', is_root: false, is_default: false },
]

const colHeaders = Object.keys(data[0])

onMounted(() => {
  if (!tableContainer.value) return

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
      { data: 'is_root', type: 'checkbox', className: 'htCenter' },
      { data: 'is_default', type: 'checkbox', className: 'htCenter' },
    ],
  })
})

onUnmounted(() => {
  if (hotInstance) {
    hotInstance.destroy()
  }
})

async function submitNewGroups() {
  // Reset messages
  _error.value = null
  _success.value = false
  _loading.value = true

  try {
    const newGroups = hotInstance
      .getSourceData()
      .filter((group) => group.name.trim())
    console.log(newGroups)

    if (newGroups.length === 0) {
      throw new Error('Нет объектов для отправки')
    }
    await axios.post(`/api/projects/${projectCode}/shot-groups/create`, newGroups)

    _success.value = true

    setTimeout(() => {
      router.push({name: 'shot-groups-by-project', params: {projectCode}})
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
      _error.value = 'Произошла ошибка при создании групп'
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
    Группы успешно созданы! Перенаправление...
  </div>

  <div v-if="_loading" class="loading-indicator">
    Создание групп...
  </div>

  <button @click="submitNewGroups" :disabled="_loading || _success">Отправить</button>
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
