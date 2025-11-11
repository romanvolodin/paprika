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

const data = [
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
  { name: '', rec_timecode: '', group: '', task: '' },
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
  })
})

onUnmounted(() => {
  if (hotInstance) {
    hotInstance.destroy()
  }
})

async function submitNewShots() {
  try {
    const newShots = hotInstance.getSourceData()
    console.log(newShots)

    if (newShots.length === 0) {
      throw new Error('Нет объектов для отправки')
    }
    await axios.post(`/api/projects/${projectCode}/shots/create`, newShots)
    router.push({name: 'shots-by-project', params: {projectCode}})
  } catch (error) {
    console.error('Ошибка:', error)
  }
}
</script>

<template>
  <div ref="tableContainer" style="width: 100%; margin: 20px auto"></div>

  <button @click="submitNewShots">Отправить</button>
</template>
