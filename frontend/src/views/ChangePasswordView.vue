<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NFormItem, NInput, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { firstValidationMessage } from '@/utils/apiError'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()

const currentPassword = ref('')
const newPassword = ref('')
const repeatPassword = ref('')
const isSubmitting = ref(false)

const isForced = computed(() => auth.mustChangePassword)
const mismatch = computed(
  () => repeatPassword.value !== '' && repeatPassword.value !== newPassword.value,
)
const canSubmit = computed(
  () =>
    currentPassword.value !== '' &&
    newPassword.value !== '' &&
    repeatPassword.value === newPassword.value,
)

async function handleSubmit() {
  if (!canSubmit.value) return
  isSubmitting.value = true
  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    message.success('Пароль изменён.')
    router.push({ name: 'project-list' })
  } catch (error) {
    message.error(firstValidationMessage(error) ?? 'Не удалось изменить пароль.')
  } finally {
    isSubmitting.value = false
  }
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="password-page">
    <form class="password-card" @submit.prevent="handleSubmit">
      <div class="password-card__brand">
        <span class="password-card__mark">P</span>
        <span>Смена пароля</span>
      </div>

      <p v-if="isForced" class="password-card__note">
        Вам выдали временный пароль. Придумайте свой, чтобы продолжить работу.
      </p>

      <n-form-item :label="isForced ? 'Временный пароль' : 'Текущий пароль'" :show-feedback="false">
        <n-input
          v-model:value="currentPassword"
          type="password"
          show-password-on="click"
          autofocus
        />
      </n-form-item>

      <n-form-item label="Новый пароль" :show-feedback="false">
        <n-input v-model:value="newPassword" type="password" show-password-on="click" />
      </n-form-item>

      <n-form-item
        label="Новый пароль ещё раз"
        :validation-status="mismatch ? 'error' : undefined"
        :feedback="mismatch ? 'Пароли не совпадают' : undefined"
      >
        <n-input v-model:value="repeatPassword" type="password" show-password-on="click" />
      </n-form-item>

      <n-button
        type="primary"
        attr-type="submit"
        block
        :loading="isSubmitting"
        :disabled="!canSubmit"
      >
        Сменить пароль
      </n-button>

      <n-button v-if="isForced" quaternary block @click="handleLogout">Выйти</n-button>
      <n-button v-else quaternary block @click="router.back()">Назад</n-button>
    </form>
  </div>
</template>

<style scoped>
.password-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
}

.password-card {
  width: 360px;
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

.password-card__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  font-size: 1.1rem;
}

.password-card__mark {
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

.password-card__note {
  margin: 0;
  color: var(--color-text-secondary);
}
</style>
