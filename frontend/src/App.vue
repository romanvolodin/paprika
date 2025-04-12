<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import BaseLayout from './layout/BaseLayout.vue'

const authStore = useAuthStore()

onMounted(() => {
  authStore.initializeAuthState()
})
</script>

<template>
  <BaseLayout />
</template>
