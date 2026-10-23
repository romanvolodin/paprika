<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const message = useMessage()

const email = ref('')
const password = ref('')
const isSubmitting = ref(false)

async function handleSubmit() {
  isSubmitting.value = true
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/projects'
    router.push(redirect)
  } catch {
    message.error('Неверный email или пароль.')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <form class="login-card" @submit.prevent="handleSubmit">
      <div class="login-card__brand">
        <span class="login-card__mark">P</span>
        <span>Paprika</span>
      </div>

      <n-form-item label="Email" :show-feedback="false">
        <n-input v-model:value="email" type="text" placeholder="you@studio.com" autofocus />
      </n-form-item>

      <n-form-item label="Пароль" :show-feedback="false">
        <n-input
          v-model:value="password"
          type="password"
          placeholder="••••••••"
          show-password-on="click"
        />
      </n-form-item>

      <n-button type="primary" attr-type="submit" block :loading="isSubmitting">
        Войти
      </n-button>
    </form>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
}

.login-card {
  width: 340px;
  max-width: calc(100vw - 32px);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6);
  background-color: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-elevated);
}

.login-card__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: var(--space-2);
}

.login-card__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-accent-text);
  font-family: var(--font-mono);
  font-weight: 700;
}
</style>
