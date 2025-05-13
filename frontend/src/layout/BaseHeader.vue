<script setup>
import { useAuthStore } from '@/stores/auth'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const auth = useAuthStore()
const _user = ref({})

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}

onMounted(() => {
  _user.value = auth.user
})
</script>

<template>
  <header>
    <div class="user" v-if="_user">
      <p>{{ _user.first_name || _user.email }}</p>
      <img class="avatar" :src="_user.avatar" alt="" />
      <button class="logout" @click="logout">𐄂</button>
    </div>
  </header>
</template>

<style scoped>
header {
  display: flex;
  justify-content: end;
  box-shadow: 0px 10px 10px #00000008;
  padding: 10px;
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
</style>
