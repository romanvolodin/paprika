<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NIcon, NInput, NSelect, NTag, useDialog, useMessage } from 'naive-ui'
import { RefreshOutline, SendOutline, TrashOutline } from '@vicons/ionicons5'
import InvitationLink from '@/components/company/InvitationLink.vue'
import * as projectsApi from '@/api/projects'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import { firstValidationMessage } from '@/utils/apiError'
import { tagColor } from '@/utils/color'
import { formatExpiry } from '@/utils/format'
import { copyToClipboard, invitationLink } from '@/utils/invitationLink'
import type { InvitationOut, ProjectOut } from '@/types/api'

const props = defineProps<{ companyId: number }>()

const store = useCompanyDetailStore()
const message = useMessage()
const dialog = useDialog()

const email = ref('')
const roleId = ref<number | null>(null)
const projectIds = ref<number[]>([])
const projectRoleId = ref<number | null>(null)
const projects = ref<ProjectOut[]>([])
const isSending = ref(false)
// The invitation just made, so its link can be copied right away.
const justInvited = ref<InvitationOut | null>(null)

const roleOptions = computed(() =>
  store.roles.map((role) => ({ label: role.name, value: role.id })),
)
const projectOptions = computed(() =>
  projects.value.map((project) => ({ label: project.name, value: project.id })),
)
const needsProjectRole = computed(() => projectIds.value.length > 0)
const canSend = computed(
  () =>
    email.value.trim() !== '' &&
    roleId.value !== null &&
    (!needsProjectRole.value || projectRoleId.value !== null),
)

onMounted(async () => {
  try {
    await store.loadInvitations(props.companyId)
    projects.value = (await projectsApi.listProjects(props.companyId, { page_size: 100 })).items
  } catch {
    message.error('Не удалось загрузить приглашения.')
  }
})

async function handleSend() {
  if (!canSend.value || roleId.value === null) return
  isSending.value = true
  try {
    justInvited.value = await store.invite(props.companyId, {
      email: email.value.trim(),
      role_id: roleId.value,
      projects: projectIds.value.map((projectId) => ({
        project_id: projectId,
        role_id: projectRoleId.value as number,
      })),
    })
    email.value = ''
    projectIds.value = []
    projectRoleId.value = null
    message.success('Приглашение создано. Передайте ссылку человеку.')
  } catch (error) {
    justInvited.value = null
    message.error(firstValidationMessage(error) ?? 'Не удалось создать приглашение.')
  } finally {
    isSending.value = false
  }
}

async function handleCopy(invitation: InvitationOut) {
  if (await copyToClipboard(invitationLink(invitation.token))) {
    message.success('Ссылка скопирована.')
  } else {
    message.warning('Не удалось скопировать ссылку.')
  }
}

async function handleRenew(invitation: InvitationOut) {
  try {
    justInvited.value = await store.renewInvitation(props.companyId, invitation.id)
    message.success('Ссылка обновлена. Старая больше не работает.')
  } catch {
    message.error('Не удалось обновить приглашение.')
  }
}

function handleRevoke(invitation: InvitationOut) {
  dialog.warning({
    title: 'Отозвать приглашение',
    content: `Отозвать приглашение для ${invitation.email}? Ссылка перестанет работать.`,
    positiveText: 'Отозвать',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.revokeInvitation(props.companyId, invitation.id)
        if (justInvited.value?.id === invitation.id) justInvited.value = null
        message.success('Приглашение отозвано.')
      } catch {
        message.error('Не удалось отозвать приглашение.')
      }
    },
  })
}
</script>

<template>
  <div class="invitations">
    <form class="invitations__form" @submit.prevent="handleSend">
      <div class="invitations__row">
        <n-input v-model:value="email" placeholder="Email" class="invitations__email" />
        <n-select
          v-model:value="roleId"
          :options="roleOptions"
          placeholder="Роль в компании"
          class="invitations__select"
        />
      </div>
      <div class="invitations__row">
        <n-select
          v-model:value="projectIds"
          :options="projectOptions"
          multiple
          clearable
          placeholder="Проекты (необязательно)"
          class="invitations__projects"
        />
        <n-select
          v-if="needsProjectRole"
          v-model:value="projectRoleId"
          :options="roleOptions"
          placeholder="Роль в проектах"
          class="invitations__select"
        />
        <n-button type="primary" attr-type="submit" :disabled="!canSend" :loading="isSending">
          <template #icon><n-icon :component="SendOutline" /></template>
          Пригласить
        </n-button>
      </div>
      <p class="invitations__hint">
        Паприка не отправляет письма: скопируйте ссылку и передайте её человеку. Ссылка работает
        ограниченное время.
      </p>
    </form>

    <div v-if="justInvited" class="invitations__result">
      <strong>{{ justInvited.email }}</strong>
      <InvitationLink :token="justInvited.token" />
    </div>

    <ul v-if="store.invitations.length > 0" class="invitations__list" aria-label="Приглашения">
      <li v-for="invitation in store.invitations" :key="invitation.id" class="invitations__item">
        <div class="invitations__info">
          <span class="invitations__who">{{ invitation.email }}</span>
          <span class="invitations__meta">
            <n-tag size="small" :color="tagColor(invitation.role.color)" round>
              {{ invitation.role.name }}
            </n-tag>
            <span v-if="invitation.projects.length > 0">
              {{ invitation.projects.map((project) => project.project_name).join(', ') }}
            </span>
            <n-tag v-if="invitation.is_expired" size="small" type="warning">Истекло</n-tag>
            <span v-else>{{ formatExpiry(invitation.expires_at) }}</span>
          </span>
        </div>
        <div class="invitations__actions">
          <n-button v-if="!invitation.is_expired" size="small" @click="handleCopy(invitation)">
            Копировать ссылку
          </n-button>
          <n-button size="small" @click="handleRenew(invitation)">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            {{ invitation.is_expired ? 'Отправить снова' : 'Обновить' }}
          </n-button>
          <n-button size="small" quaternary type="error" @click="handleRevoke(invitation)">
            <template #icon><n-icon :component="TrashOutline" /></template>
            Отозвать
          </n-button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.invitations {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.invitations__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.invitations__row {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.invitations__email {
  width: 260px;
}

.invitations__select {
  width: 200px;
}

.invitations__projects {
  width: 320px;
}

.invitations__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.invitations__result {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
}

.invitations__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.invitations__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.invitations__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.invitations__who {
  font-weight: 500;
}

.invitations__meta {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  flex-wrap: wrap;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.invitations__actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
</style>
