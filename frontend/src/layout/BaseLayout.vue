<script setup>
import { RouterView, useRoute } from 'vue-router'
import BaseHeader from '@/layout/BaseHeader.vue'

const route = useRoute()
console.log(route)
</script>

<template>
  <BaseHeader v-if="route.name !== 'login'" />
  <RouterView />
</template>
