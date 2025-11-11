<script setup>
import { useAuthStore } from '@/stores/auth'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useDark, useToggle } from '@vueuse/core'

const isDark = useDark()
const toggleDark = useToggle(isDark)

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const _user = ref({})
const _projectCode = ref(null)

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}

watch(
  () => route.params.projectCode,
  () => {
    if (route.params.projectCode) {
      _projectCode.value = route.params.projectCode
    }
  },
)

function goToHome() {
  _projectCode.value = null
  router.push({ name: 'home' })
}

onMounted(() => {
  _user.value = auth.user
})
</script>

<template>
  <header>
    <nav>
      <router-link :to="{ name: 'home' }" @click="goToHome">Проекты</router-link>
      <div v-if="_projectCode" class="project-subnav">
        <b>{{ _projectCode }}</b>
        <b>🢒</b>
        <router-link
          :to="{ name: 'shot-groups-by-project', params: { projectCode: _projectCode } }"
        >
          Группы
        </router-link>
        <router-link :to="{ name: 'shots-by-project', params: { projectCode: _projectCode } }">
          Шоты
        </router-link>
        <router-link :to="{ name: 'tasks-by-project', params: { projectCode: _projectCode } }">
          Задачи
        </router-link>
      </div>
    </nav>

    <div class="extra">
      <div @click="toggleDark()" class="theme-toggler">
        {{ isDark ? '🌙' : '☀️' }}
      </div>

      <div class="user" v-if="_user">
        <p>{{ _user.first_name || _user.email }}</p>
        <img class="avatar" :src="_user.avatar" alt="" />
        <button class="logout" @click="logout">𐄂</button>
      </div>
    </div>
  </header>
</template>

<style scoped>
* {
  text-decoration: none;
}
header {
  display: flex;
  justify-content: space-between;
  box-shadow: 0px 10px 10px #00000008;
  padding: 10px;
}
nav {
  display: flex;
  gap: 20px;
}
.extra {
  display: flex;
  align-items: center;
  gap: 40px;
}
.theme-toggler {
  display: flex;
  justify-content: start;
  align-items: center;
  cursor: pointer;
  border: 2px solid #d5d5d5;
  border-radius: 50vh;
  padding: 0 2px;
  padding-bottom: 1px;
  width: 48px;
  height: 28px;
}
html.dark .theme-toggler {
  justify-content: end;
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  border-radius: 50vh;
  aspect-ratio: 1;
  width: 40px;
  object-fit: cover;
}
.logout {
  padding: 0 5px;
}
.project-subnav {
  display: flex;
  gap: 20px;
}
</style>
