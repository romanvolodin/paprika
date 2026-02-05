<script setup>
import { useShot } from '@/composables/useShot'
import axios from '@/config/axiosConfig'
import { useAuthStore } from '@/stores/auth'
import { nextTick, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import ChatArea from '@/components/chat/ChatArea.vue'

const route = useRoute()
const projectCode = route.params.projectCode
const shotName = route.params.shotName

const { shot, isLoading, error, fetchShot } = useShot(projectCode, shotName)

const auth = useAuthStore()
const _user = ref({})

const _versions = ref([])
const _chat = ref([])
const _all_users = ref([])
const _selected_version = ref(null)

onMounted(async () => {
  _user.value = auth.user
  await fetchAllUsers()
  await fetchShot()
  if (shot.value) {
    _versions.value = shot.value.versions
    _selected_version.value = shot.value.versions.at(0)
    _chat.value = shot.value.chat_messages
    localStorage.setItem('lastViewedShot', `${shotName}`)
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

function setSelectedVersion(version) {
  _selected_version.value = version
}

watchEffect(() => {
  if (shot.value) {
    document.title = shot.value.name
  }
})
</script>

<template>
  <div v-if="isLoading" class="empty">Загрузка...</div>

  <div v-else-if="error" class="error">
    {{ error }}
  </div>

  <div v-else class="wrapper">
    <div v-if="_versions.length === 0" class="empty">
      <p>Версий пока нет</p>

      <router-link :to="{name: 'upload-version', params: { projectCode, shotName }}">
        <div class="version version-upload">
          <p>Загрузить версию</p>
        </div>
      </router-link>
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
        <router-link :to="{name: 'upload-version', params: { projectCode, shotName }}">
        <div class="version version-upload">
          <p>Загрузить версию</p>
        </div>
        </router-link>

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

    <ChatArea :chat-data="_chat" :all-users="_all_users"/>
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
</style>
