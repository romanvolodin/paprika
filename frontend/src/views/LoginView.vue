<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import axios from 'axios'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const error_message = ref('')

const login = async () => {
  try {
    const response = await axios.post('http://localhost:8000/api/token/', {
      email: email.value,
      password: password.value,
    })
    const token = response.data.access

    localStorage.setItem('auth_token', token)

    await axios
      .get('http://localhost:8000/api/me/', {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then(function (response) {
        authStore.setUser(response.data)
      })
      .catch(console.log)

    let url = route.query.next
    if (!url) {
      url = '/'
    }
    router.push(url)
  } catch (error) {
    error_message.value = error.response.data
  }
}
</script>

<template>
  <main>
    <form @submit.prevent="login" method="post">
      <p v-if="error_message">{{ error_message }}</p>
      <p>
        <input required v-model="email" type="email" name="email" placeholder="your@email.com" />
      </p>
      <p>
        <input required v-model="password" type="password" name="password" placeholder="password" />
      </p>
      <p><button type="submit">login</button></p>
    </form>
  </main>
</template>

<style scoped>
main {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
}
</style>
