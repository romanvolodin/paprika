<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const errorMessage = ref('')

const login = async () => {
  errorMessage.value = '' // Очищаем предыдущие ошибки

  try {
    const success = await authStore.login({
      email: email.value,
      password: password.value,
    })
    if (success) {
      let url = route.query.next
      if (!url) {
        url = '/'
      }
      router.push(url)
    }
  } catch (error) {
    errorMessage.value = error
  }
}
</script>

<template>
  <main>
    <form @submit.prevent="login" method="post">
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
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
* {
  padding: 10px 20px;
  font-size: 24px;
}
main {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
}
.error-message {
  margin-bottom: 10px;
  border: 1px solid red;
  border-radius: 4px;
  background-color: #ffe6e6;
  padding: 10px;
  color: red;
}
</style>
