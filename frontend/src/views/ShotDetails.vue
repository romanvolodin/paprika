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

    <div class="chat">
      <div class="message" v-for="message in _shot.chat_messages" :key="message.created_at">
        <p class="author">{{ message.created_by }}</p>
        <blockquote class="quote" v-if="message.reply_to">
          <p>Автор</p>
          <p>{{ message.reply_to }}</p>
        </blockquote>
        <div class="text">
          {{ message.text }}
        </div>
        <p class="date-time">
          {{
            new Date(message.created_at).toLocaleString('ru-ru', {
              month: 'short',
              day: '2-digit',
              hour: '2-digit',
              minute: 'numeric',
            })
          }}
        </p>
      </div>
    </div>
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
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  width: 100%;
  min-width: 200px;
}
.message {
  border-radius: 10px;
  border-bottom-left-radius: 0;
  background-color: hsl(83, 10%, 92%);
  padding: 10px;
}
.author {
  font-weight: bold;
}
.quote {
  margin: 5px 0;
  border-left: 4px solid hsl(83, 35%, 50%);
  border-radius: 5px;
  background-color: hsl(83, 15%, 80%);
  padding: 3px 6px;
}
.date-time {
  opacity: 0.4;
  text-align: right;
}
</style>
