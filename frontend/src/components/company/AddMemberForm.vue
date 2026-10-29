<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NInput, NSelect } from 'naive-ui'
import { AddOutline, KeyOutline } from '@vicons/ionicons5'
import { generatePassword } from '@/utils/password'
import type { CompanyMemberCreateIn, RoleOut } from '@/types/api'

defineProps<{ roles: RoleOut[]; isSubmitting: boolean }>()

const emit = defineEmits<{ submit: [value: CompanyMemberCreateIn] }>()

const email = ref('')
const firstName = ref('')
const lastName = ref('')
const password = ref('')
const roleId = ref<number | null>(null)

const canSubmit = computed(
  () =>
    email.value.trim() !== '' &&
    firstName.value.trim() !== '' &&
    lastName.value.trim() !== '' &&
    password.value !== '' &&
    roleId.value !== null,
)

function handleSubmit() {
  if (!canSubmit.value || roleId.value === null) return
  emit('submit', {
    email: email.value.trim(),
    first_name: firstName.value.trim(),
    last_name: lastName.value.trim(),
    password: password.value,
    role_id: roleId.value,
  })
}

// Called by the parent once the member is added, to get a clean form.
function reset() {
  email.value = ''
  firstName.value = ''
  lastName.value = ''
  password.value = ''
  roleId.value = null
}

defineExpose({ reset })
</script>

<template>
  <form class="add-member" @submit.prevent="handleSubmit">
    <div class="add-member__row">
      <n-input v-model:value="email" type="text" placeholder="Email" class="add-member__email" />
      <n-input v-model:value="firstName" placeholder="Имя" class="add-member__name" />
      <n-input v-model:value="lastName" placeholder="Фамилия" class="add-member__name" />
    </div>
    <div class="add-member__row">
      <n-input
        v-model:value="password"
        placeholder="Временный пароль"
        class="add-member__password"
      />
      <n-button @click="password = generatePassword()">
        <template #icon><n-icon :component="KeyOutline" /></template>
        Сгенерировать
      </n-button>
      <n-select
        v-model:value="roleId"
        :options="roles.map((role) => ({ label: role.name, value: role.id }))"
        placeholder="Роль"
        class="add-member__role"
      />
      <n-button type="primary" attr-type="submit" :disabled="!canSubmit" :loading="isSubmitting">
        <template #icon><n-icon :component="AddOutline" /></template>
        Добавить
      </n-button>
    </div>
    <p class="add-member__hint">
      Человек сменит временный пароль при первом входе. Если такой email уже есть в Паприке, его
      владелец просто окажется в вашей компании: имя и пароль не используются.
    </p>
  </form>
</template>

<style scoped>
.add-member {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.add-member__row {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.add-member__email {
  width: 260px;
}

.add-member__name,
.add-member__password {
  width: 180px;
}

.add-member__role {
  width: 180px;
}

.add-member__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}
</style>
