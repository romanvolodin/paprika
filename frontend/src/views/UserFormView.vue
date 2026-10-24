<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NInput,
  NSwitch,
  NAvatar,
  NFormItem,
  NIcon,
  useMessage,
  useDialog,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { CameraOutline, TrashOutline, ArrowBackOutline } from '@vicons/ionicons5'
import * as usersApi from '@/api/users'
import { useDynamicPageTitle } from '@/composables/useDynamicPageTitle'
import type { UserOut } from '@/types/api'

const props = defineProps<{ userId?: number }>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const isEditing = computed(() => props.userId !== undefined)

const formRef = ref<FormInst | null>(null)
const isLoading = ref(false)
const isSaving = ref(false)

const email = ref('')
const password = ref('')
const firstName = ref('')
const lastName = ref('')
const isActive = ref(true)
const loadedFullName = ref('')

useDynamicPageTitle(loadedFullName)

const rules: FormRules = {
  email: [{ required: true, message: 'Укажите email', trigger: ['input', 'blur'] }],
  first_name: [{ required: true, message: 'Укажите имя', trigger: ['input', 'blur'] }],
  last_name: [{ required: true, message: 'Укажите фамилию', trigger: ['input', 'blur'] }],
}

// Naive UI's <n-form> validates against a model object keyed by each
// <n-form-item>'s `path` - the individual refs above stay the source of
// truth (and what v-model binds to); this just mirrors them for validation.
const formModel = computed(() => ({
  email: email.value,
  first_name: firstName.value,
  last_name: lastName.value,
}))

const existingAvatarUrl = ref<string | null | undefined>(null)
const newAvatarFile = ref<File | null>(null)
const newAvatarPreviewUrl = ref<string | null>(null)
const removeAvatar = ref(false)

const avatarPreview = computed(() => newAvatarPreviewUrl.value ?? existingAvatarUrl.value)
const avatarInput = ref<HTMLInputElement | null>(null)

function initials(): string {
  return `${firstName.value[0] ?? ''}${lastName.value[0] ?? ''}`.toUpperCase() || '?'
}

function pickAvatar() {
  avatarInput.value?.click()
}

function handleAvatarChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  newAvatarFile.value = file
  newAvatarPreviewUrl.value = URL.createObjectURL(file)
  removeAvatar.value = false
}

function clearAvatar() {
  newAvatarFile.value = null
  newAvatarPreviewUrl.value = null
  existingAvatarUrl.value = null
  removeAvatar.value = true
}

async function loadUser(userId: number) {
  isLoading.value = true
  try {
    const user: UserOut = await usersApi.getUser(userId)
    email.value = user.email
    firstName.value = user.first_name
    lastName.value = user.last_name
    isActive.value = user.is_active
    existingAvatarUrl.value = user.avatar
    loadedFullName.value = `${user.first_name} ${user.last_name}`.trim()
  } catch {
    message.error('Не удалось загрузить пользователя.')
    router.push({ name: 'users-list' })
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  isSaving.value = true
  try {
    if (isEditing.value) {
      await usersApi.updateUser(props.userId!, {
        first_name: firstName.value,
        last_name: lastName.value,
        is_active: isActive.value,
        remove_avatar: removeAvatar.value,
        avatar: newAvatarFile.value,
      })
      message.success('Изменения сохранены.')
    } else {
      await usersApi.createUser({
        email: email.value,
        password: password.value || null,
        firstName: firstName.value,
        lastName: lastName.value,
        avatar: newAvatarFile.value,
      })
      message.success('Пользователь создан.')
    }
    router.push({ name: 'users-list' })
  } catch {
    message.error('Не удалось сохранить пользователя. Проверьте введённые данные.')
  } finally {
    isSaving.value = false
  }
}

function confirmDelete() {
  dialog.warning({
    title: 'Удалить пользователя',
    content: 'Это действие необратимо.',
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await usersApi.deleteUser(props.userId!)
        message.success('Пользователь удалён.')
        router.push({ name: 'users-list' })
      } catch {
        message.error('Не удалось удалить пользователя.')
      }
    },
  })
}

onMounted(() => {
  if (props.userId !== undefined) {
    loadUser(props.userId)
  }
})
</script>

<template>
  <div class="user-form">
    <button class="user-form__back" type="button" @click="router.push({ name: 'users-list' })">
      <n-icon :component="ArrowBackOutline" />
      К списку пользователей
    </button>

    <h1 class="user-form__title">
      {{ isEditing ? 'Редактирование пользователя' : 'Новый пользователь' }}
    </h1>

    <div class="user-form__avatar">
      <n-avatar
        round
        :size="72"
        :src="avatarPreview ?? undefined"
        style="font-family: var(--font-mono); font-size: 22px"
      >
        <template v-if="!avatarPreview">{{ initials() }}</template>
      </n-avatar>
      <div class="user-form__avatar-actions">
        <input
          ref="avatarInput"
          type="file"
          accept="image/*"
          hidden
          @change="handleAvatarChange"
        />
        <n-button size="small" @click="pickAvatar">
          <template #icon><n-icon :component="CameraOutline" /></template>
          Загрузить фото
        </n-button>
        <n-button v-if="avatarPreview" size="small" quaternary @click="clearAvatar">
          <template #icon><n-icon :component="TrashOutline" /></template>
          Удалить
        </n-button>
      </div>
    </div>

    <n-form ref="formRef" :model="formModel" :rules="rules" label-placement="top" @submit.prevent="handleSubmit">
      <n-form-item label="Email" path="email">
        <n-input v-model:value="email" :disabled="isEditing" placeholder="user@studio.com" />
      </n-form-item>

      <n-form-item v-if="!isEditing" label="Пароль (необязательно)">
        <n-input
          v-model:value="password"
          type="password"
          show-password-on="click"
          placeholder="Оставьте пустым для инвайт-флоу"
        />
      </n-form-item>

      <div class="user-form__row">
        <n-form-item label="Имя" path="first_name">
          <n-input v-model:value="firstName" />
        </n-form-item>
        <n-form-item label="Фамилия" path="last_name">
          <n-input v-model:value="lastName" />
        </n-form-item>
      </div>

      <n-form-item v-if="isEditing" label="Активен">
        <n-switch v-model:value="isActive" />
      </n-form-item>

      <div class="user-form__actions">
        <n-button
          v-if="isEditing"
          quaternary
          type="error"
          style="margin-right: auto"
          @click="confirmDelete"
        >
          Удалить пользователя
        </n-button>
        <n-button @click="router.push({ name: 'users-list' })">Отмена</n-button>
        <n-button type="primary" attr-type="submit" :loading="isSaving">Сохранить</n-button>
      </div>
    </n-form>
  </div>
</template>

<style scoped>
.user-form {
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.user-form__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  cursor: pointer;
  padding: 0;
  align-self: flex-start;
}

.user-form__back:hover {
  color: var(--color-text);
}

.user-form__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.user-form__avatar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.user-form__avatar-actions {
  display: flex;
  gap: var(--space-2);
}

.user-form__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

@media (max-width: 480px) {
  .user-form__row {
    grid-template-columns: 1fr;
  }
}

.user-form__actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}
</style>
