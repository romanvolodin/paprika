<script setup>
import { useShot } from '@/composables/useShot'
import axios from '@/config/axiosConfig'
import { useAuthStore } from '@/stores/auth'
import { nextTick, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'

import { useTextareaAutosize } from '@vueuse/core'

import MessageBubble from '@/components/chat/MessageBubble.vue'

import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

const route = useRoute()
const projectCode = route.params.projectCode
const shotName = route.params.shotName

const { shot, isLoading, error, fetchShot } = useShot(projectCode, shotName)

const auth = useAuthStore()
const _user = ref({})

const _versions = ref([])
const _chat = ref([])
const _reply_to_message = ref(null)
const _reply_to_id = ref(null)
const _all_users = ref([])
const _attachments = ref([])
const _selected_version = ref(null)
const _versionUploading = ref(false)
const _chatArea = ref(null)

function scrollToLastMessage() {
  if (_chatArea.value) {
    _chatArea.value.scrollTo({
      top: _chatArea.value.scrollHeight,
      behavior: 'smooth',
    })
  }
}

watch(_chat, () => {
  nextTick(scrollToLastMessage)
})

const { textarea: userMessageTextarea, input: _message } = useTextareaAutosize({
  styleProp: 'minHeight',
})

const getAuthorById = (id) => {
  return _all_users.value.find((user) => {
    return user.id === id
  })
}

onMounted(async () => {
  _user.value = auth.user
  await fetchAllUsers()
  await fetchShot()
  if (shot.value) {
    _versions.value = shot.value.versions
    _selected_version.value = shot.value.versions.at(0)
    _chat.value = shot.value.chat_messages
    scrollToLastMessage()
  }
})

async function fetchAllUsers() {
  try {
    const response = await axios.get(`/api/users/`)
    _all_users.value = response.data.results
  } catch (error) {
    error.value = `${error.status}: ${error.response.data.detail}`
  }
}

async function sendMessage() {
  if (!_message.value && !_attachments.value.length) return

  const formData = new FormData()

  formData.append('shot', shot.value.id)
  formData.append('text', _message.value)
  formData.append('created_by', _user.value.id)
  formData.append('created_at', new Date().toISOString())

  if (_reply_to_id.value) {
    formData.append('reply_to', _reply_to_id.value)
  }

  _attachments.value.forEach((file) => {
    formData.append(`attachments`, file)
  })

  try {
    await axios.post(`/api/projects/${projectCode}/shots/${shotName}/chat_messages/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    _message.value = ''
    _attachments.value = []
    _attachmentPreviews.value = []
    _reply_to_id.value = null
    _reply_to_message.value = null

    await fetchShot()
    _chat.value = shot.value.chat_messages
  } catch (error) {
    console.error('Ошибка при отправке сообщения:', error)
  }
}

function adminEditUrl(shot_id) {
  return `http://paprika-app.ru/admin/core/shot/${shot_id}/change/`
}

function replyToMessage(message) {
  _reply_to_id.value = message.id
  _reply_to_message.value = {
    id: message.id,
    text: message.text,
    created_by: message.created_by,
  }
}

function exitReplyMode() {
  _reply_to_id.value = null
  _reply_to_message.value = null
}

function setAttachments(event) {
  _attachments.value = Array.from(event.target.files)
}

function setSelectedVersion(version) {
  _selected_version.value = version
}

const handleVersionUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  _versionUploading.value = true

  const formData = new FormData()
  formData.append('shot', shot.value.id)
  formData.append('file', file)

  try {
    await axios.post(`/api/projects/${projectCode}/shots/${shotName}/versions/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    await fetchShot()
    _selected_version.value = shot.value.versions.at(0)
    _versions.value = shot.value.versions
    _chat.value = shot.value.chat_messages
    scrollToLastMessage()
  } catch (error) {
    console.error('Ошибка загрузки:', error)
  } finally {
    _versionUploading.value = false
  }
}

const _attachmentPreviews = ref([])

const handleFileChange = (event) => {
  setAttachments(event)

  const files = Array.from(event.target.files)
  _attachmentPreviews.value = []

  files.forEach((file) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      _attachmentPreviews.value.push({
        name: file.name,
        type: file.type,
        url: e.target.result,
      })
    }
    reader.readAsDataURL(file)
  })
}

watchEffect(() => {
  if (shot.value) {
    document.title = shot.value.name
  }
})

function formatAuthorName(authorId) {
  if (!authorId) {
    return ''
  }

  const author = getAuthorById(authorId)
  return `${author.first_name} ${author.last_name}`
}

function formatDateTime(datetime) {

  return new Date(datetime).toLocaleString('ru-ru', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: 'numeric',
  })

}

function replaceToMdash(e) {
  const el = e.target
  const processedMessage = el.value.replace(/--/g, '—')
  if (processedMessage === _message.value) return
  _message.value = processedMessage
}
</script>

<template>
  <div v-if="isLoading" class="empty">Загрузка...</div>

  <div v-else-if="error" class="error">
    {{ error }}
  </div>

  <div v-else class="wrapper">
    <div v-if="_versions.length === 0" class="empty">
      <p>Версий пока нет</p>

      <form method="post" enctype="multipart/form-data">
        <input type="file" id="uploading-version" hidden @change="handleVersionUpload" />
        <label for="uploading-version" class="version version-upload">
          <div v-if="_versionUploading" class="version-loader">
            <div class="spinner"></div>
            <p>Загружается...</p>
          </div>
          <p v-else>Загрузить версию</p>
        </label>
      </form>
    </div>

    <div v-else class="player">
      <video
        v-if="_selected_version.video"
        :src="_selected_version.video"
        controls
        muted
        autoplay
        loop
      ></video>
      <img v-else :src="_selected_version.preview" alt="" />

      <div class="versions-panel">
        <form method="post" enctype="multipart/form-data">
          <input type="file" id="uploading-version" hidden @change="handleVersionUpload" />
          <label for="uploading-version" class="version version-upload">
            <div v-if="_versionUploading" class="version-loader">
              <div class="spinner"></div>
              <p>Загружается...</p>
            </div>

            <p v-else>Загрузить версию</p>
          </label>
        </form>

        <div
          class="version"
          v-for="version in _versions"
          :key="version.id"
          @click="setSelectedVersion(version)"
        >
          <img :src="version.preview" />
          <p>{{ version.name }}</p>
        </div>
      </div>
    </div>

    <div class="chat">
      <a v-if="shot" :href="adminEditUrl(shot.id)">{{ shot.name }} в админке</a>
      <div v-if="_chat.length === 0" class="empty">Сообщений пока нет</div>
      <div v-else class="chat-area" ref="_chatArea">
        <div class="messages">
          <MessageBubble
            v-for="message in _chat"
            :key="message.created_at"
            :author="formatAuthorName(message.created_by)"
            :body="md.render(message.text)"
            :datetime="formatDateTime(message.created_at)"
            :attachments="message.attachments"
            :reply-to-author="formatAuthorName(message.reply_to_display?.created_by)"
            :reply-to-text="message.reply_to_display?.text"
            @reply="replyToMessage(message)"
          />
        </div>
      </div>
      <blockquote class="reply-mode" v-if="_reply_to_message">
        <div>
          <p>
            В ответ
            {{
              getAuthorById(_reply_to_message.created_by).first_name +
              ' ' +
              getAuthorById(_reply_to_message.created_by).last_name
            }}
          </p>
          <p class="truncate">{{ _reply_to_message.text }}</p>
        </div>
        <button class="exit-reply-mode" @click="exitReplyMode">⨯</button>
      </blockquote>

      <div v-if="_attachmentPreviews.length" class="attachments-wrapper">
        <div v-for="attachment in _attachmentPreviews" :key="attachment" class="attachment">
          <img :src="attachment.url" />
        </div>
        <p style="margin-left: 40px; grid-column-start: 1; grid-column-end: -1">
          Введите описание ↓
        </p>
      </div>

      <form
        @submit.prevent="sendMessage"
        class="input-field"
        method="post"
        enctype="multipart/form-data"
      >
        <div class="form-row">
          <label>
            <input
              type="file"
              id="uploading-attachments"
              @change="handleFileChange"
              multiple
              hidden
            />
            📎
          </label>
          <textarea
            ref="userMessageTextarea"
            v-model="_message"
            class="resize-none"
            placeholder="Сообщение..."
            @input="replaceToMdash"
          ></textarea>
          <button type="submit">➜</button>
        </div>
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
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
}
.wrapper {
  display: grid;
  grid-template-columns: 1fr 400px;
  width: 100%;
}
.player > video {
  background-color: #000;
  aspect-ratio: 16 / 9;
  width: 100%;
  max-width: 1400px;
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
  overflow-y: scroll;
}
.messages {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}
.form-row {
  display: flex;
  font-size: 18px;
}
.form-row > label,
.form-row > button {
  padding: 10px;
  font-size: inherit;
}
.form-row > label:hover,
.form-row > button:hover {
  background-color: #eee;
}
.form-row > textarea {
  flex-grow: 1;
}
.reply-mode {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.exit-reply-mode {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 10px;
  outline: none;
  border: none;
  background: none;
  width: 40px;
  height: 40px;
  font-size: 30px;
}
.versions-panel {
  display: flex;
  gap: 5px;
  padding: 0 5px;
}
.version {
  position: relative;
  filter: brightness(0.75);
  cursor: pointer;
  border-radius: 7px;
  width: 160px;
  height: 90px;
  overflow: hidden;
}
.version:hover {
  filter: brightness(1);
}
.version img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.version p {
  position: absolute;
  top: 0;
  padding: 5px 10px;
  color: white;
}
.version-upload {
  display: flex;
  justify-content: center;
  align-items: center;
  border: 1px dashed gray;
}
.version-upload:hover {
  background-color: #eee;
}
.version-upload p {
  position: relative;
  color: #ccc;
  font-size: 14px;
}
.version-loader {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  width: 25px;
  height: 25px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.truncate {
  /* FIXME: Ширина должна подстраиваться под ширину чата, а не быть фиксированной */
  width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
