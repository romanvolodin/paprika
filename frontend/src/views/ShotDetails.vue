<script setup>
import axios from '@/config/axiosConfig'
import { useAuthStore } from '@/stores/auth'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectCode = route.params.projectCode
const shotName = route.params.shotName

const auth = useAuthStore()
const _user = ref({})

const _shot = ref(null)
const _versions = ref([])
const _chat = ref([])
const _loaded = ref(false)
const _error = ref(null)
const _message = ref('')

const _all_users = ref([])

const getAuthorById = (id) => {
  return _all_users.value.find((user) => {
    return user.id === id
  })
}

onMounted(async () => {
  _user.value = auth.user
  await fetchAllUsers()
  await fetchShot()
})

async function fetchAllUsers() {
  try {
    const response = await axios.get(`/api/users/`)
    _all_users.value = response.data.results
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
  }
}

async function fetchShot() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shots/${shotName}`)
    _shot.value = response.data
    _versions.value = response.data.versions
    _chat.value = response.data.chat_messages
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
    _shot.value = null
  } finally {
    _loaded.value = true
  }
}

async function postMessage(message) {
  try {
    await axios.post(`/api/projects/${projectCode}/shots/${shotName}/chat_messages/`, message)
  } catch (error) {
    console.log(error)
  }
}

async function sendMessage() {
  if (!_message.value) {
    return
  }
  const msg = {
    shot: _shot.value.id,
    reply_to: null,
    text: _message.value,
    created_at: new Date().toISOString(),
    created_by: _user.value.id,
  }
  console.log(msg)

  await postMessage(msg)
  await fetchShot()
  _message.value = ''
}

function formatText(text) {
  return text.replace(/\n/g, '<br>')
}

function adminEditUrl(shot_id) {
  return `http://paprika-app.ru/admin/core/shot/${shot_id}/change/`
}
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else class="wrapper">
    <div v-if="_versions.length === 0" class="empty">Версий пока нет</div>
    <div v-else class="player">
      <video
        v-if="_versions[0].video"
        :src="_versions[0].video"
        controls
        muted
        autoplay
        loop
      ></video>
      <img v-else :src="_versions[0].preview" alt="" />
    </div>

    <div class="chat">
      <a :href="adminEditUrl(_shot.id)">{{ _shot.name }} в админке</a>
      <div v-if="_chat.length === 0" class="empty">Сообщений пока нет</div>
      <div v-else class="chat-area">
        <div class="messages">
          <div class="message" v-for="message in _chat" :key="message.created_at">
            <p class="author">
              {{
                getAuthorById(message.created_by).first_name +
                ' ' +
                getAuthorById(message.created_by).last_name
              }}
            </p>
            <blockquote class="quote" v-if="message.reply_to">
              <p>Автор</p>
              <p>Текст цитаты</p>
            </blockquote>
            <div class="text" v-html="formatText(message.text)"></div>
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
      <form @submit.prevent="sendMessage" class="input-field">
        <input v-model.trim="_message" placeholder="Сообщение..." />
        <button type="submit">➜</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.error {
  margin: 2rem;
  border: 1px solid #c41212;
  border-radius: 4px;
  background-color: #ffe6e6;
  padding: 1rem;
  color: #c41212;
  font-weight: bold;
}
.empty {
  display: flex;
  flex-grow: 1;
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
.player > img {
  width: 100%;
}
.chat {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 200px;
  height: 900px;
}
.chat-area {
  flex-grow: 1;
}
.messages {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
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
.input-field {
  display: flex;
  padding: 20px;
  font-size: 18px;
}
.input-field > input,
.input-field > button {
  padding: 10px;
  font-size: inherit;
}
.input-field > input {
  flex-grow: 1;
}
</style>
