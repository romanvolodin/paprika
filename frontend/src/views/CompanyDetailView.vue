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
} from 'naive-ui'
import { ArrowBackOutline, TrashOutline } from '@vicons/ionicons5'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import AddMemberForm from '@/components/company/AddMemberForm.vue'
import CompanyInvitationsSection from '@/components/company/CompanyInvitationsSection.vue'
import ShotStatusesSection from '@/components/shots/ShotStatusesSection.vue'
import TaskStatusesSection from '@/components/tasks/TaskStatusesSection.vue'
import TaskTypesSection from '@/components/tasks/TaskTypesSection.vue'
import { useCompanyPermissions } from '@/composables/useCompanyPermissions'
import { useDynamicPageTitle } from '@/composables/useDynamicPageTitle'
import { firstValidationMessage } from '@/utils/apiError'
import { tagColor } from '@/utils/color'
import { slugify } from '@/utils/slugify'
import type { CompanyMemberCreateIn, CompanyMemberOut } from '@/types/api'

const props = defineProps<{ companyId: number }>()

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const store = useCompanyDetailStore()
const {
  canEditCompany,
  canManagePipeline,
  canManageRoles,
  canManageMembers,
  canRemoveMember,
  canChangeMemberRole,
} = useCompanyPermissions(computed(() => store.company))

const roleOptions = computed(() =>
  store.roles.map((role) => ({ label: role.name, value: role.id })),
)

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

async function handleRoleChange(member: CompanyMemberOut, roleId: number) {
  try {
    await store.updateMemberRole(props.companyId, member.user_id, roleId)
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

// --- Add member --------------------------------------------------------

const addMemberForm = ref<InstanceType<typeof AddMemberForm> | null>(null)
const isAddingMember = ref(false)

async function handleAddMember(input: CompanyMemberCreateIn) {
  isAddingMember.value = true
  try {
    await store.addMember(props.companyId, input)
    message.success('Участник добавлен.')
    addMemberForm.value?.reset()
  } catch (error) {
    message.error(
      firstValidationMessage(error) ??
        'Не удалось добавить участника. Возможно, он уже состоит в компании.',
    )
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

      <add-member-form
        v-if="canManageMembers"
        ref="addMemberForm"
        :roles="store.roles"
        :is-submitting="isAddingMember"
        @submit="handleAddMember"
      />
    </section>

    <section v-if="canManageMembers" class="company-detail__section">
      <h2 class="company-detail__heading">Приглашения</h2>
      <company-invitations-section :company-id="props.companyId" />
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Роли</h2>
      <div class="company-detail__roles">
        <n-tag v-for="role in store.roles" :key="role.id" :color="tagColor(role.color)" round>
          {{ role.name }}
        </n-tag>
      </div>
      <div>
        <n-button
          size="small"
          @click="router.push({ name: 'company-roles', params: { id: props.companyId } })"
        >
          {{ canManageRoles ? 'Настроить роли' : 'Посмотреть роли' }}
        </n-button>
      </div>
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Статусы кадров</h2>
      <shot-statuses-section :company-id="props.companyId" :can-edit="canManagePipeline" />
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Типы задач</h2>
      <task-types-section :company-id="props.companyId" :can-edit="canManagePipeline" />
    </section>

    <section class="company-detail__section">
      <h2 class="company-detail__heading">Статусы задач</h2>
      <task-statuses-section :company-id="props.companyId" :can-edit="canManagePipeline" />
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

.company-detail__roles {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.company-detail__add-member {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}
</style>
