<script setup lang="ts">
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
import { AddOutline, ArrowBackOutline, CameraOutline, TrashOutline } from '@vicons/ionicons5'
import { useProjectDetailStore } from '@/stores/projectDetail'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import ShotGroupsSection from '@/components/shots/ShotGroupsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { MEMBERSHIP_ROLE_LABELS, MEMBERSHIP_ROLE_OPTIONS } from '@/constants/membershipRoles'
import type { CompanyMemberOut, ProjectMemberOut, ProjectMembershipRole } from '@/types/api'

const props = defineProps<{ projectId: number }>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const store = useProjectDetailStore()
const currentCompany = useCurrentCompanyStore()
const { canEditProject, canWrite, canManageMembers, canRemoveMember, canChangeMemberRole } =
  useProjectPermissions(computed(() => store.members))

onMounted(() => {
  store.fetch(props.projectId)
})

const companySlug = computed(
  () =>
    currentCompany.companies.find((company) => company.id === store.project?.company_id)?.slug ??
    null,
)

function openShots() {
  if (!store.project || !companySlug.value) return
  router.push({
    name: 'shot-list',
    params: { companySlug: companySlug.value, projectCode: store.project.code },
  })
}

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
    await store.updateProject(props.projectId, {
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

async function handleRoleChange(member: ProjectMemberOut, role: ProjectMembershipRole) {
  try {
    await store.updateMemberRole(props.projectId, member.user_id, role)
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
        await store.removeMember(props.projectId, member.user_id)
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
            value: member.role,
            options: MEMBERSHIP_ROLE_OPTIONS,
            size: 'small',
            onUpdateValue: (role: ProjectMembershipRole) => handleRoleChange(member, role),
          })
        : h(
            NTag,
            { size: 'small', round: true },
            { default: () => MEMBERSHIP_ROLE_LABELS[member.role] },
          ),
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
const newMemberRole = ref<ProjectMembershipRole>('executor')
const isAddingMember = ref(false)

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
  if (!newMemberUserId.value) return

  isAddingMember.value = true
  try {
    await store.addMember(props.projectId, {
      user_id: newMemberUserId.value,
      role: newMemberRole.value,
    })
    message.success('Участник добавлен.')
    newMemberUserId.value = null
    newMemberRole.value = 'executor'
  } catch {
    message.error('Не удалось добавить участника.')
  } finally {
    isAddingMember.value = false
  }
}
</script>

<template>
  <div v-if="store.project" class="project-detail">
    <button
      class="project-detail__back"
      type="button"
      @click="router.push({ name: 'project-list' })"
    >
      <n-icon :component="ArrowBackOutline" />
      К списку проектов
    </button>

    <div class="project-detail__heading-row">
      <h1 class="project-detail__title">{{ store.project.name }}</h1>
      <span class="mono project-detail__code">{{ store.project.code }}</span>
      <n-button v-if="companySlug" size="small" class="project-detail__shots" @click="openShots">
        Кадры
      </n-button>
    </div>

    <section class="project-detail__section">
      <h2 class="project-detail__heading">Настройки</h2>
      <n-form
        ref="formRef"
        :model="formModel"
        :rules="rules"
        label-placement="top"
        :disabled="!canEditProject"
        @submit.prevent="handleSaveProject"
      >
        <div class="project-detail__cover">
          <div class="project-detail__cover-preview">
            <img v-if="coverPreview" :src="coverPreview" alt="" />
            <n-icon v-else :component="CameraOutline" size="28" />
          </div>
          <div v-if="canEditProject" class="project-detail__cover-actions">
            <input
              ref="coverInput"
              type="file"
              accept="image/png,image/jpeg,image/gif"
              class="project-detail__cover-input"
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
        <p class="project-detail__hint">Код нельзя изменить после создания проекта.</p>

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

    <section class="project-detail__section">
      <h2 class="project-detail__heading">Участники</h2>

      <n-data-table
        :columns="columns"
        :data="store.members"
        :loading="store.isLoading"
        :bordered="false"
        :row-key="(row: ProjectMemberOut) => row.id"
      />

      <div v-if="canManageMembers" class="project-detail__add-member">
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
          :options="MEMBERSHIP_ROLE_OPTIONS"
          style="max-width: 180px"
        />
        <n-button
          type="primary"
          :disabled="!newMemberUserId"
          :loading="isAddingMember"
          @click="handleAddMember"
        >
          <template #icon><n-icon :component="AddOutline" /></template>
          Добавить
        </n-button>
      </div>
    </section>

    <section class="project-detail__section">
      <h2 class="project-detail__heading">Группы кадров</h2>
      <shot-groups-section :project-id="props.projectId" :can-write="canWrite" />
    </section>
  </div>
  <p v-else-if="store.isLoading" class="project-detail__loading">Загрузка…</p>
</template>

<style scoped>
.project-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 720px;
}

.project-detail__back {
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

.project-detail__back:hover {
  color: var(--color-text);
}

.project-detail__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.project-detail__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.project-detail__shots {
  margin-left: auto;
}
.project-detail__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-detail__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.project-detail__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.project-detail__hint {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-detail__cover {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.project-detail__cover-preview {
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

.project-detail__cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.project-detail__cover-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.project-detail__cover-input {
  display: none;
}

.project-detail__loading {
  color: var(--color-text-secondary);
}

.project-detail__add-member {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}
</style>
