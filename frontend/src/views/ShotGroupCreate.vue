<script setup>
import axios from '@/config/axiosConfig'
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode

const _loaded = ref(false)
const _error = ref(null)

const newShotGroups = [
  {
    name: 'New-shot-group',
    is_default: false,
    is_root: true,
  },
  {
    name: 'New-shot-group2',
  },
]

async function createShotGroups() {
  try {
    const response = await axios.post(
      `/api/projects/${projectCode}/shot-groups/create`,
      newShotGroups,
    )
    console.log(response.data)
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  } finally {
    _loaded.value = true
  }
}
</script>

<template>
  <button @click="createShotGroups">Create ShotGroups</button>
</template>
