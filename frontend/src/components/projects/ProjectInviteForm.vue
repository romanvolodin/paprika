<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NInput, NSelect } from 'naive-ui'
import { SendOutline } from '@vicons/ionicons5'
import { COMPANY_LEVEL_CODES } from '@/constants/permissions'
import type { RoleOut } from '@/types/api'

const props = defineProps<{ roles: RoleOut[]; isSubmitting: boolean }>()

const emit = defineEmits<{ submit: [value: { email: string; role_id: number }] }>()

const email = ref('')
const roleId = ref<number | null>(null)

// A person invited to a project gets the same role in the company, so a
// role with company rights can only be given by inviting to the company.
const options = computed(() =>
  props.roles
    .filter(
      (role) =>
        !role.sees_all_projects &&
        !role.permissions.some((code) => (COMPANY_LEVEL_CODES as readonly string[]).includes(code)),
    )
    .map((role) => ({ label: role.name, value: role.id })),
)

const canSubmit = computed(() => email.value.trim() !== '' && roleId.value !== null)

function handleSubmit() {
  if (!canSubmit.value || roleId.value === null) return
  emit('submit', { email: email.value.trim(), role_id: roleId.value })
}

function reset() {
  email.value = ''
  roleId.value = null
}

defineExpose({ reset })
</script>

<template>
  <form class="project-invite" @submit.prevent="handleSubmit">
    <n-input
      v-model:value="email"
      placeholder="Email приглашаемого"
      class="project-invite__email"
    />
    <n-select
      v-model:value="roleId"
      :options="options"
      placeholder="Роль"
      class="project-invite__role"
    />
    <n-button type="primary" attr-type="submit" :disabled="!canSubmit" :loading="isSubmitting">
      <template #icon><n-icon :component="SendOutline" /></template>
      Пригласить
    </n-button>
  </form>
</template>

<style scoped>
.project-invite {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.project-invite__email {
  width: 260px;
}

.project-invite__role {
  width: 180px;
}
</style>
