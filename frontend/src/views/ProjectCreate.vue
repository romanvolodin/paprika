<script setup>
import { onMounted, ref } from 'vue'
import axios from '@/config/axiosConfig'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'
import { useRouter } from 'vue-router'

const router = useRouter()
const projectsStore = useProjectsStore()

const auth = useAuthStore()
const _user = ref({})

const _name = ref('')
const _code = ref('')

onMounted(async () => {
  _user.value = auth.user
})

async function postProject(project) {
  try {
    await axios.post('/api/projects/', project)
  } catch (error) {
    console.log(error)
  }
}

function createProject() {
  const project = {
    name: _name.value,
    code: _code.value,
    created_at: new Date().toISOString(),
    created_by: _user.value.id,
  }

  postProject(project)
  projectsStore.fetchProjects()
  router.push({ name: 'home' })
}
</script>

<template>
  <h1>Создать проект</h1>
  <form class="form" @submit.prevent="createProject()">
    <label for="name">Название</label>
    <input type="text" name="name" v-model="_name" />

    <label for="code">Код</label>
    <input type="text" name="code" v-model="_code" />

    <button class="submit-button" type="submit">Создать</button>
  </form>
</template>

<style scoped>
.form {
  display: grid;
  grid-template-columns: 150px 350px;
  gap: 10px;
  margin: 0 auto;
}
.submit-button {
  grid-column-end: -1;
}
</style>
