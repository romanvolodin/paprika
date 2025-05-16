<script setup>
import { onMounted, ref } from 'vue'
import { useShotsStore } from '@/stores/shots'
import { useRoute } from 'vue-router'

const route = useRoute()
const _shot = ref(null)

const shotsStore = useShotsStore()

onMounted(async () => {
  _shot.value = shotsStore.shots.find((shot) => {
    return shot.name === route.params.shotName
  })
})
</script>

<template>
  {{ _shot }}
</template>
