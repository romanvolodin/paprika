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
  <div v-if="_shot" class="wrapper">
    <div class="player">
      <video :src="_shot.versions[0].video" controls muted autoplay loop></video>
    </div>

    <div class="chat">messages</div>
  </div>

  <div v-else class="empty">Загрузка...</div>
</template>

<style scoped>
.empty {
  display: flex;
  justify-content: center;
  align-items: center;
}
.wrapper {
  display: grid;
  grid-template-columns: 1fr 400px;
  width: 100%;
}
.player > video {
  width: 100%;
}
.chat {
  width: 300px;
  min-width: 200px;
}
</style>
