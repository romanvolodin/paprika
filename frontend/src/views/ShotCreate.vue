<script setup>
import axios from '@/config/axiosConfig'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const projectCode = route.params.projectCode

const newShots = ref([])

function addShot() {
  newShots.value.push({
    name: '',
    rec_timecode: '',
    task: '',
  })
}

function removeShot(index) {
  newShots.value.splice(index, 1)
}

async function submitNewShots() {
  try {
    if (newShots.value.length === 0) {
      throw new Error('Нет объектов для отправки')
    }
    const response = await axios.post(`/api/projects/${projectCode}/shots/create`, newShots.value)
    console.log('Ответ сервера:', response.data)
  } catch (error) {
    console.error('Ошибка:', error)
  }
}
</script>

<template>
  <h1>Новые шоты</h1>

  <button @click="addShot" class="btn-add">+ Добавить шот</button>

  <div v-if="newShots.length > 0">
    <div v-for="(shot, index) in newShots" :key="index">
      <input v-model="shot.name" placeholder="SHOT_0010" />
      <input v-model="shot.rec_timecode" placeholder="00:00:00:00" />
      <input v-model="shot.task" placeholder="Задача" />
      <button @click="removeShot(index)" class="btn-remove">⨯</button>
    </div>
  </div>

  <hr />

  <button @click="submitNewShots" class="btn-submit">Отправить на сервер</button>
</template>

<style scoped>
.btn-add,
.btn-submit,
.btn-remove {
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
}
</style>
