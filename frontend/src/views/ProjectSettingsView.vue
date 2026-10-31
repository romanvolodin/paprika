<script setup lang="ts">
import InvitationLink from '@/components/company/InvitationLink.vue'
import ProjectInviteForm from '@/components/projects/ProjectInviteForm.vue'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAvatar,
  NButton,
  NDataTable,
  NDatePicker,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NSelect,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import { AddOutline, CameraOutline, TrashOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import { useProjectPageStore } from '@/stores/projectPage'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { firstValidationMessage } from '@/utils/apiError'
import type { CompanyMemberOut, InvitationOut, ProjectMemberOut } from '@/types/api'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const store = useProjectPageStore()
const { project } = storeToRefs(store)
const {
  canEditProject,
  canDeleteProject,
  canOpenSettings,
  canManageMembers,
  canRemoveMember,
  canChangeMemberRole,
} = useProjectPermissions(project)

const roleOptions = computed(() =>
  store.roles.map((role) => ({ label: role.name, value: role.id })),
)

onMounted(() => {
  store.loadCompanyMembers()
})

// --- Project settings ---------------------------------------------------

const formRef = ref<FormInst | null>(null)
const isSaving = ref(false)
const name = ref('')
const description = ref('')
const startDate = ref<string | null>(null)
const deadline = ref<string | null>(null)
const isActive = ref(true)

const existingCoverUrl = ref<string | null>(null)
const newCoverFile = ref<File | null>(null)
const newCoverPreviewUrl = ref<string | null>(null)
const removeCover = ref(false)
const coverInput = ref<HTMLInputElement | null>(null)

const coverPreview = computed(() => newCoverPreviewUrl.value ?? existingCoverUrl.value)

function pickCover() {
  coverInput.value?.click()
}

function handleCoverChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  newCoverFile.value = file
  newCoverPreviewUrl.value = URL.createObjectURL(file)
  removeCover.value = false
}

function clearCover() {
  newCoverFile.value = null
  newCoverPreviewUrl.value = null
  existingCoverUrl.value = null
  removeCover.value = true
}

watch(
  () => store.project,
  (project) => {
    if (!project) return
    name.value = project.name
    description.value = project.description
    startDate.value = project.start_date
    deadline.value = project.deadline
    isActive.value = project.is_active
    existingCoverUrl.value = project.cover ?? null
  },
  { immediate: true },
)

const rules: FormRules = {
  name: [{ required: true, message: 'Укажите название', trigger: ['input', 'blur'] }],
}

const formModel = computed(() => ({ name: name.value }))

async function handleSaveProject() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  isSaving.value = true
  try {
    await store.updateProject({
      name: name.value,
      description: description.value,
      startDate: startDate.value,
      deadline: deadline.value,
      isActive: isActive.value,
      removeCover: removeCover.value,
      cover: newCoverFile.value,
    })
    message.success('Проект обновлён.')
  } catch {
    message.error('Не удалось сохранить изменения.')
  } finally {
    isSaving.value = false
  }
}

// --- Members -------------------------------------------------------------

function initials(member: { first_name: string; last_name: string }): string {
  return `${member.first_name[0] ?? ''}${member.last_name[0] ?? ''}`.toUpperCase()
}

async function handleRoleChange(member: ProjectMemberOut, roleId: number) {
  try {
    await store.updateMemberRole(member.user_id, roleId)
    message.success('Роль обновлена.')
  } catch {
    message.error('Не удалось изменить роль.')
  }
}

function confirmRemoveMember(member: ProjectMemberOut) {
  dialog.warning({
    title: 'Удалить участника',
    content: `Удалить ${member.first_name} ${member.last_name} из проекта?`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.removeMember(member.user_id)
        message.success('Участник удалён.')
      } catch {
        message.error('Не удалось удалить участника.')
      }
    },
  })
}

const columns = computed<DataTableColumns<ProjectMemberOut>>(() => [
  {
    title: '',
    key: 'avatar',
    width: 48,
    render: (member) =>
      h(
        NAvatar,
        {
          round: true,
          size: 32,
          src: member.avatar ?? undefined,
          style: { fontFamily: 'var(--font-mono)', fontSize: '12px' },
        },
        member.avatar ? undefined : { default: () => initials(member) },
      ),
  },
  {
    title: 'Имя',
    key: 'name',
    render: (member) => `${member.first_name} ${member.last_name}`,
  },
  {
    title: 'Email',
    key: 'email',
    render: (member) => h('span', { class: 'mono' }, member.email),
  },
  {
    title: 'Роль',
    key: 'role',
    width: 200,
    render: (member) =>
      canChangeMemberRole(member.user_id)
        ? h(NSelect, {
            value: member.role.id,
            options: roleOptions.value,
            size: 'small',
            onUpdateValue: (roleId: number) => handleRoleChange(member, roleId),
          })
        : h(NTag, { size: 'small', round: true }, { default: () => member.role.name }),
  },
  {
    title: '',
    key: 'actions',
    width: 48,
    render: (member) =>
      canRemoveMember(member.user_id)
        ? h(
            NButton,
            {
              quaternary: true,
              circle: true,
              size: 'small',
              onClick: () => confirmRemoveMember(member),
            },
            { icon: () => h(NIcon, { component: TrashOutline }) },
          )
        : null,
  },
])

// --- Add member ------------------------------------------------------------

// Only an existing member of the project's company can be added (the API
// rejects anyone else), so the picker is built from the company's member
// list rather than a system-wide user search - and only offers people who
// aren't already on the project.
const availableCompanyMembers = computed<CompanyMemberOut[]>(() =>
  store.companyMembers.filter(
    (companyMember) => !store.members.some((member) => member.user_id === companyMember.user_id),
  ),
)

const memberOptions = computed(() =>
  availableCompanyMembers.value.map((companyMember) => ({
    value: companyMember.user_id,
    label: `${companyMember.first_name} ${companyMember.last_name}`,
    member: companyMember,
  })),
)

const newMemberUserId = ref<number | null>(null)
const newMemberRole = ref<number | null>(null)
const isAddingMember = ref(false)

const inviteForm = ref<InstanceType<typeof ProjectInviteForm> | null>(null)
const isInviting = ref(false)
const justInvited = ref<InvitationOut | null>(null)

async function handleInvite(input: { email: string; role_id: number }) {
  isInviting.value = true
  try {
    justInvited.value = await store.inviteToProject(input)
    inviteForm.value?.reset()
    message.success('Приглашение создано. Передайте ссылку человеку.')
  } catch (error) {
    justInvited.value = null
    message.error(firstValidationMessage(error) ?? 'Не удалось создать приглашение.')
  } finally {
    isInviting.value = false
  }
}

function renderMemberOption(option: SelectOption) {
  const member = (option as { member?: CompanyMemberOut }).member
  return h('div', { style: 'display: flex; align-items: center; gap: 8px;' }, [
    h(
      NAvatar,
      {
        round: true,
        size: 24,
        src: member?.avatar ?? undefined,
        style: { fontFamily: 'var(--font-mono)', fontSize: '10px' },
      },
      member?.avatar ? undefined : { default: () => (member ? initials(member) : '') },
    ),
    h('span', null, option.label as string),
  ])
}

async function handleAddMember() {
  if (!newMemberUserId.value || !newMemberRole.value) return

  isAddingMember.value = true
  try {
    await store.addMember({
      user_id: newMemberUserId.value,
      role_id: newMemberRole.value,
    })
    message.success('Участник добавлен.')
    newMemberUserId.value = null
    newMemberRole.value = null
  } catch {
    message.error('Не удалось добавить участника.')
  } finally {
    isAddingMember.value = false
  }
}

// --- Delete project --------------------------------------------------------

const isDeleting = ref(false)

function confirmDeleteProject() {
  if (!store.project) return
  dialog.warning({
    title: 'Удалить проект',
    content: `Удалить проект ${store.project.name} (${store.project.code})? Вместе с ним будут удалены все его кадры, версии, задачи и чаты. Это действие необратимо.`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      isDeleting.value = true
      try {
        await store.deleteProject()
        message.success('Проект удалён.')
        router.push({ name: 'project-list' })
      } catch {
        message.error('Не удалось удалить проект.')
      } finally {
        isDeleting.value = false
      }
    },
  })
}
</script>

<template>
  <div v-if="!canOpenSettings" class="project-settings__message">
    У вас нет прав на настройки проекта.
  </div>
  <div v-else-if="store.project" class="project-settings">
    <section class="project-settings__section">
      <h2 class="project-settings__heading">Настройки</h2>
      <n-form
        ref="formRef"
        :model="formModel"
        :rules="rules"
        label-placement="top"
        :disabled="!canEditProject"
        @submit.prevent="handleSaveProject"
      >
        <div class="project-settings__cover">
          <div class="project-settings__cover-preview">
            <img v-if="coverPreview" :src="coverPreview" alt="" />
            <n-icon v-else :component="CameraOutline" size="28" />
          </div>
          <div v-if="canEditProject" class="project-settings__cover-actions">
            <input
              ref="coverInput"
              type="file"
              accept="image/png,image/jpeg,image/gif"
              class="project-settings__cover-input"
              @change="handleCoverChange"
            />
            <n-button size="small" @click="pickCover">
              {{ coverPreview ? 'Заменить обложку' : 'Загрузить обложку' }}
            </n-button>
            <n-button v-if="coverPreview" size="small" quaternary @click="clearCover">
              <template #icon><n-icon :component="TrashOutline" /></template>
            </n-button>
          </div>
        </div>

        <n-form-item label="Название" path="name">
          <n-input v-model:value="name" />
        </n-form-item>

        <n-form-item label="Код">
          <n-input :value="store.project.code" disabled />
        </n-form-item>
        <p class="project-settings__hint">Код нельзя изменить после создания проекта.</p>

        <n-form-item label="Описание">
          <n-input v-model:value="description" type="textarea" />
        </n-form-item>

        <n-form-item label="Начало">
          <n-date-picker
            v-model:formatted-value="startDate"
            value-format="yyyy-MM-dd"
            type="date"
            clearable
            style="width: 100%"
          />
        </n-form-item>

        <n-form-item label="Дедлайн">
          <n-date-picker
            v-model:formatted-value="deadline"
            value-format="yyyy-MM-dd"
            type="date"
            clearable
            style="width: 100%"
          />
        </n-form-item>

        <n-form-item label="Активен">
          <n-switch v-model:value="isActive" />
        </n-form-item>

        <n-button v-if="canEditProject" type="primary" attr-type="submit" :loading="isSaving">
          Сохранить
        </n-button>
      </n-form>
    </section>

    <section class="project-settings__section">
      <h2 class="project-settings__heading">Участники</h2>

      <n-data-table
        :columns="columns"
        :data="store.members"
        :loading="store.isLoading"
        :bordered="false"
        :row-key="(row: ProjectMemberOut) => row.id"
      />

      <div v-if="canManageMembers" class="project-settings__add-member">
        <n-select
          v-model:value="newMemberUserId"
          filterable
          clearable
          placeholder="Выбрать участника компании"
          style="max-width: 320px"
          :options="memberOptions"
          :render-label="renderMemberOption"
        />
        <n-select
          v-model:value="newMemberRole"
          :options="roleOptions"
          placeholder="Роль"
          style="max-width: 180px"
        />
        <n-button
          type="primary"
          :disabled="!newMemberUserId || !newMemberRole"
          :loading="isAddingMember"
          @click="handleAddMember"
        >
          <template #icon><n-icon :component="AddOutline" /></template>
          Добавить
        </n-button>
      </div>

      <div v-if="canManageMembers" class="project-settings__invite">
        <h3 class="project-settings__subheading">Пригласить в проект</h3>
        <p class="project-settings__hint project-settings__hint--plain">
          Для тех, кого ещё нет в компании. Человек войдёт в компанию с той же ролью, поэтому здесь
          только роли без прав на управление компанией. Паприка не отправляет письма: скопируйте
          ссылку и передайте её человеку.
        </p>
        <project-invite-form
          ref="inviteForm"
          :roles="store.roles"
          :is-submitting="isInviting"
          @submit="handleInvite"
        />
        <div v-if="justInvited" class="project-settings__invited">
          <strong>{{ justInvited.email }}</strong>
          <InvitationLink :token="justInvited.token" />
        </div>
      </div>
    </section>

    <section v-if="canDeleteProject" class="project-settings__section">
      <h2 class="project-settings__heading">Удаление проекта</h2>
      <div class="project-settings__danger">
        <p class="project-settings__hint project-settings__hint--plain">
          Проект будет удалён вместе со всеми кадрами, версиями, задачами и чатами. Отменить это
          нельзя.
        </p>
        <n-button type="error" secondary :loading="isDeleting" @click="confirmDeleteProject">
          Удалить проект
        </n-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.project-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 720px;
}

.project-settings__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.project-settings__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.project-settings__hint {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-settings__cover {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.project-settings__cover-preview {
  width: 120px;
  height: 68px;
  border-radius: var(--radius-md);
  background: var(--color-bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.project-settings__cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.project-settings__cover-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.project-settings__cover-input {
  display: none;
}

.project-settings__invite {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.project-settings__subheading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.project-settings__invited {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
}

.project-settings__add-member {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.project-settings__message {
  color: var(--color-text-secondary);
}

.project-settings__danger {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
}

.project-settings__hint--plain {
  margin: 0;
}
</style>
