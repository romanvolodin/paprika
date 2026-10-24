<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAvatar,
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NSelect,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import { AddOutline, ArrowBackOutline, TrashOutline } from '@vicons/ionicons5'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import ShotStatusesSection from '@/components/shots/ShotStatusesSection.vue'
import TaskStatusesSection from '@/components/tasks/TaskStatusesSection.vue'
import TaskTypesSection from '@/components/tasks/TaskTypesSection.vue'
import { useCompanyPermissions } from '@/composables/useCompanyPermissions'
import { useDynamicPageTitle } from '@/composables/useDynamicPageTitle'
import { useUserSearchOptions } from '@/composables/useUserSearchOptions'
import { MEMBERSHIP_ROLE_LABELS, MEMBERSHIP_ROLE_OPTIONS } from '@/constants/membershipRoles'
import { slugify } from '@/utils/slugify'
import type { CompanyMemberOut, CompanyMembershipRole, UserOut } from '@/types/api'

const props = defineProps<{ companyId: number }>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const store = useCompanyDetailStore()
const { canEditCompany, canManageMembers, canRemoveMember, canChangeMemberRole } =
  useCompanyPermissions(computed(() => store.members))

useDynamicPageTitle(() => (store.company?.id === props.companyId ? store.company.name : null))

onMounted(() => {
  store.fetch(props.companyId)
})

// --- Company settings ------------------------------------------------------

const formRef = ref<FormInst | null>(null)
const isSaving = ref(false)
const name = ref('')
const slug = ref('')
const slugTouchedManually = ref(false)

function syncFormFromStore() {
  name.value = store.company?.name ?? ''
  slug.value = store.company?.slug ?? ''
  // The company already has a slug when we load it - further edits to
  // `name` shouldn't silently overwrite an intentional existing slug.
  slugTouchedManually.value = true
}

watch(
  () => store.company,
  (company) => {
    if (company) syncFormFromStore()
  },
  { immediate: true },
)

const rules: FormRules = {
  name: [{ required: true, message: 'Укажите название', trigger: ['input', 'blur'] }],
}

const formModel = computed(() => ({ name: name.value }))

function handleNameInput(value: string) {
  name.value = value
  if (!slugTouchedManually.value) {
    slug.value = slugify(value)
  }
}

function handleSlugInput(value: string) {
  slug.value = value
  slugTouchedManually.value = true
}

async function handleSaveCompany() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  isSaving.value = true
  try {
    await store.updateCompany(props.companyId, { name: name.value, slug: slug.value || null })
    message.success('Компания обновлена.')
  } catch {
    message.error('Не удалось сохранить изменения.')
  } finally {
    isSaving.value = false
  }
}

// --- Members -----------------------------------------------------------

function initials(member: CompanyMemberOut): string {
  return `${member.first_name[0] ?? ''}${member.last_name[0] ?? ''}`.toUpperCase()
}

async function handleRoleChange(member: CompanyMemberOut, role: CompanyMembershipRole) {
  try {
    await store.updateMemberRole(props.companyId, member.user_id, role)
    message.success('Роль обновлена.')
  } catch {
    message.error('Не удалось изменить роль.')
  }
}

function confirmRemoveMember(member: CompanyMemberOut) {
  dialog.warning({
    title: 'Удалить участника',
    content: `Удалить ${member.first_name} ${member.last_name} из компании?`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.removeMember(props.companyId, member.user_id)
        message.success('Участник удалён.')
      } catch {
        message.error('Не удалось удалить участника.')
      }
    },
  })
}

const columns = computed<DataTableColumns<CompanyMemberOut>>(() => [
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
            onUpdateValue: (role: CompanyMembershipRole) => handleRoleChange(member, role),
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

// --- Add member --------------------------------------------------------

const userSearch = useUserSearchOptions()
const newMemberUserId = ref<number | null>(null)
const newMemberRole = ref<CompanyMembershipRole>('executor')
const isAddingMember = ref(false)

function renderUserOption(option: SelectOption) {
  const user = (option as { user?: UserOut }).user
  return h('div', { style: 'display: flex; align-items: center; gap: 8px;' }, [
    h(
      NAvatar,
      {
        round: true,
        size: 24,
        src: user?.avatar ?? undefined,
        style: { fontFamily: 'var(--font-mono)', fontSize: '10px' },
      },
      user?.avatar
        ? undefined
        : {
            default: () =>
              user ? `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase() : '',
          },
    ),
    h('span', null, option.label as string),
  ])
}

async function handleAddMember() {
  if (!newMemberUserId.value) return

  isAddingMember.value = true
  try {
    await store.addMember(props.companyId, {
      user_id: newMemberUserId.value,
      role: newMemberRole.value,
    })
    message.success('Участник добавлен.')
    newMemberUserId.value = null
    newMemberRole.value = 'executor'
  } catch {
    message.error('Не удалось добавить участника. Возможно, он уже состоит в компании.')
  } finally {
    isAddingMember.value = false
  }
}
</script>

<template>
  <div v-if="store.company" class="company-detail">
    <button
      class="company-detail__back"
      type="button"
      @click="router.push({ name: 'company-list' })"
    >
      <n-icon :component="ArrowBackOutline" />
      К списку компаний
    </button>

    <h1 class="company-detail__title">{{ store.company.name }}</h1>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Настройки</h2>
      <n-form
        ref="formRef"
        :model="formModel"
        :rules="rules"
        label-placement="top"
        :disabled="!canEditCompany"
        @submit.prevent="handleSaveCompany"
      >
        <n-form-item label="Название" path="name">
          <n-input :value="name" @update:value="handleNameInput" />
        </n-form-item>
        <n-form-item label="Slug">
          <n-input :value="slug" @update:value="handleSlugInput" />
        </n-form-item>
        <n-button v-if="canEditCompany" type="primary" attr-type="submit" :loading="isSaving">
          Сохранить
        </n-button>
      </n-form>
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Участники</h2>

      <n-data-table
        :columns="columns"
        :data="store.members"
        :loading="store.isLoading"
        :bordered="false"
        :row-key="(row: CompanyMemberOut) => row.id"
      />

      <div v-if="canManageMembers" class="company-detail__add-member">
        <n-select
          v-model:value="newMemberUserId"
          filterable
          remote
          clearable
          placeholder="Найти пользователя по имени или email"
          style="max-width: 320px"
          :loading="userSearch.loading.value"
          :options="userSearch.options.value"
          :render-label="renderUserOption"
          @search="userSearch.search"
          @focus="userSearch.loadInitial"
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

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Статусы кадров</h2>
      <shot-statuses-section :company-id="props.companyId" :can-edit="canEditCompany" />
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Типы задач</h2>
      <task-types-section :company-id="props.companyId" :can-edit="canEditCompany" />
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Статусы задач</h2>
      <task-statuses-section :company-id="props.companyId" :can-edit="canEditCompany" />
    </section>
  </div>
  <p v-else-if="store.isLoading" class="company-detail__loading">Загрузка…</p>
</template>

<style scoped>
.company-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 720px;
}

.company-detail__back {
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

.company-detail__back:hover {
  color: var(--color-text);
}

.company-detail__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.company-detail__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.company-detail__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.company-detail__loading {
  color: var(--color-text-secondary);
}

.company-detail__add-member {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}
</style>
