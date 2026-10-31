<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { isAxiosError } from 'axios'
import { NButton, NFormItem, NInput, NSpin, useMessage } from 'naive-ui'
import * as invitationsApi from '@/api/invitations'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import { firstValidationMessage } from '@/utils/apiError'
import type { InvitationInfoOut } from '@/types/api'

const props = defineProps<{ token: string }>()

type State = 'loading' | 'invalid' | 'ready'

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()
const currentCompany = useCurrentCompanyStore()

const state = ref<State>('loading')
const info = ref<InvitationInfoOut | null>(null)
const isWorking = ref(false)

const firstName = ref('')
const lastName = ref('')
const password = ref('')
const repeatPassword = ref('')

const signedInAsInvited = computed(
  () => auth.currentUser?.email.toLowerCase() === info.value?.email.toLowerCase(),
)
const mismatch = computed(
  () => repeatPassword.value !== '' && repeatPassword.value !== password.value,
)
const canRegister = computed(
  () =>
    firstName.value.trim() !== '' &&
    lastName.value.trim() !== '' &&
    password.value !== '' &&
    password.value === repeatPassword.value,
)

onMounted(async () => {
  try {
    info.value = await invitationsApi.getInviteInfo(props.token)
    state.value = 'ready'
  } catch {
    state.value = 'invalid'
  }
})

async function finish() {
  if (!info.value) return
  await currentCompany.refreshCompanies()
  currentCompany.selectCompany(info.value.company_id)
  router.push({ name: 'project-list' })
}

async function handleAccept() {
  isWorking.value = true
  try {
    await invitationsApi.acceptInvite(props.token)
    message.success('Вы в компании.')
    await finish()
  } catch (error) {
    message.error(
      isAxiosError(error) && error.response?.status === 410
        ? 'Приглашение уже использовано или устарело.'
        : 'Не удалось принять приглашение.',
    )
  } finally {
    isWorking.value = false
  }
}

async function handleRegister() {
  if (!info.value || !canRegister.value) return
  isWorking.value = true
  try {
    await invitationsApi.registerByInvite(props.token, {
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      password: password.value,
    })
    await auth.login(info.value.email, password.value)
    message.success('Добро пожаловать!')
    await finish()
  } catch (error) {
    message.error(firstValidationMessage(error) ?? 'Не удалось создать аккаунт.')
  } finally {
    isWorking.value = false
  }
}

function goToLogin() {
  router.push({ name: 'login', query: { redirect: `/invite/${props.token}` } })
}

async function handleLogout() {
  await auth.logout()
}
</script>

<template>
  <div class="invite-page">
    <div class="invite-card">
      <div class="invite-card__brand">
        <span class="invite-card__mark">P</span>
        <span>Приглашение</span>
      </div>

      <n-spin v-if="state === 'loading'" class="invite-card__spin" />

      <p v-else-if="state === 'invalid'" class="invite-card__note">
        Эта ссылка недействительна. Попросите прислать приглашение ещё раз.
      </p>

      <template v-else-if="info">
        <p class="invite-card__lead">
          Вас приглашают в компанию <strong>{{ info.company_name }}</strong> с ролью «{{
            info.role_name
          }}».
        </p>
        <p v-if="info.project_names.length > 0" class="invite-card__note">
          Проекты: {{ info.project_names.join(', ') }}.
        </p>

        <p v-if="info.status !== 'pending'" class="invite-card__note">
          {{
            info.status === 'accepted'
              ? 'Это приглашение уже использовано.'
              : 'Срок приглашения истёк.'
          }}
          Попросите прислать новое.
        </p>

        <template v-else-if="auth.isAuthenticated">
          <template v-if="signedInAsInvited">
            <n-button type="primary" block :loading="isWorking" @click="handleAccept">
              Принять приглашение
            </n-button>
          </template>
          <template v-else>
            <p class="invite-card__note">
              Вы вошли как {{ auth.currentUser?.email }}, а приглашение для {{ info.email }}.
              Выйдите и войдите под нужной почтой.
            </p>
            <n-button block @click="handleLogout">Выйти</n-button>
          </template>
        </template>

        <template v-else-if="info.account_exists">
          <p class="invite-card__note">
            У {{ info.email }} уже есть аккаунт. Войдите, чтобы принять приглашение.
          </p>
          <n-button type="primary" block @click="goToLogin">Войти</n-button>
        </template>

        <form v-else class="invite-card__form" @submit.prevent="handleRegister">
          <p class="invite-card__note">
            Создайте аккаунт для {{ info.email }}, чтобы принять приглашение.
          </p>
          <n-form-item label="Имя" :show-feedback="false">
            <n-input v-model:value="firstName" />
          </n-form-item>
          <n-form-item label="Фамилия" :show-feedback="false">
            <n-input v-model:value="lastName" />
          </n-form-item>
          <n-form-item label="Пароль" :show-feedback="false">
            <n-input v-model:value="password" type="password" show-password-on="click" />
          </n-form-item>
          <n-form-item
            label="Пароль ещё раз"
            :validation-status="mismatch ? 'error' : undefined"
            :feedback="mismatch ? 'Пароли не совпадают' : undefined"
          >
            <n-input v-model:value="repeatPassword" type="password" show-password-on="click" />
          </n-form-item>
          <n-button
            type="primary"
            attr-type="submit"
            block
            :loading="isWorking"
            :disabled="!canRegister"
          >
            Создать аккаунт и принять
          </n-button>
        </form>
      </template>
    </div>
  </div>
</template>

<style scoped>
.invite-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
}

.invite-card {
  width: 380px;
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

.invite-card__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 600;
  font-size: 1.1rem;
}

.invite-card__mark {
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

.invite-card__lead,
.invite-card__note {
  margin: 0;
}

.invite-card__note {
  color: var(--color-text-secondary);
}

.invite-card__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.invite-card__spin {
  align-self: center;
}
</style>
