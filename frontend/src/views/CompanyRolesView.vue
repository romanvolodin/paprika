<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { isAxiosError } from 'axios'
import { NButton, NButtonGroup, NEmpty, NIcon, NSpin, useDialog, useMessage } from 'naive-ui'
import { AddOutline, ArrowBackOutline } from '@vicons/ionicons5'
import RoleEditor, { type RoleFormValue } from '@/components/roles/RoleEditor.vue'
import RoleMatrix from '@/components/roles/RoleMatrix.vue'
import { useCompanyPermissions } from '@/composables/useCompanyPermissions'
import { useDynamicPageTitle } from '@/composables/useDynamicPageTitle'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import type { RoleOut } from '@/types/api'

const props = defineProps<{ companyId: number }>()

type Mode = 'list' | 'matrix'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const store = useCompanyDetailStore()
const { canManageRoles } = useCompanyPermissions(computed(() => store.company))

useDynamicPageTitle(() =>
  store.company?.id === props.companyId ? `Роли — ${store.company.name}` : null,
)

const mode = ref<Mode>('list')
const selectedRoleId = ref<number | null>(null)
const isCreating = ref(false)
const isSaving = ref(false)

const isReady = computed(() => store.company?.id === props.companyId)

const selectedRole = computed<RoleOut | null>(
  () => store.roles.find((role) => role.id === selectedRoleId.value) ?? null,
)

onMounted(async () => {
  await Promise.all([store.fetch(props.companyId), store.loadPermissionCatalog()])
})

// Show the first role once the list is there, and move off a role that is gone.
watch(
  () => store.roles,
  (roles) => {
    if (isCreating.value) return
    if (!roles.some((role) => role.id === selectedRoleId.value)) {
      selectedRoleId.value = roles[0]?.id ?? null
    }
  },
  { immediate: true },
)

function selectRole(roleId: number) {
  isCreating.value = false
  selectedRoleId.value = roleId
  mode.value = 'list'
}

function startCreating() {
  isCreating.value = true
  selectedRoleId.value = null
  mode.value = 'list'
}

function describeError(error: unknown, fallback: string): string {
  if (!isAxiosError(error) || error.response?.status !== 409) return fallback
  const data = error.response.data?.detail
  const text: string = Array.isArray(data) ? (data[0]?.msg ?? '') : String(data ?? '')
  if (text.includes('name')) return 'Роль с таким названием уже есть в компании.'
  if (text.includes('edit roles')) {
    return 'В компании должен остаться хотя бы один человек, который может настраивать роли.'
  }
  return 'Роль назначена людям, удалить её нельзя. Сначала назначьте им другую роль.'
}

async function handleSave(value: RoleFormValue) {
  isSaving.value = true
  try {
    if (isCreating.value) {
      const created = await store.createRole(props.companyId, value)
      isCreating.value = false
      selectedRoleId.value = created.id
      message.success('Роль создана.')
    } else if (selectedRole.value) {
      await store.updateRole(props.companyId, selectedRole.value.id, value)
      message.success('Роль сохранена.')
    }
  } catch (error) {
    message.error(describeError(error, 'Не удалось сохранить роль. Проверьте введённые данные.'))
  } finally {
    isSaving.value = false
  }
}

function handleRemove() {
  const role = selectedRole.value
  if (!role) return
  dialog.warning({
    title: 'Удалить роль',
    content: `Удалить роль «${role.name}»?`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.removeRole(props.companyId, role.id)
        message.success('Роль удалена.')
      } catch (error) {
        message.error(describeError(error, 'Не удалось удалить роль.'))
      }
    },
  })
}

function usage(role: RoleOut): string {
  return `${role.company_members_count} в компании · ${role.project_members_count} в проектах`
}
</script>

<template>
  <div v-if="isReady" class="company-roles">
    <button
      class="company-roles__back"
      type="button"
      @click="router.push({ name: 'company-detail', params: { id: props.companyId } })"
    >
      <n-icon :component="ArrowBackOutline" />
      К компании
    </button>

    <div class="company-roles__header">
      <h1 class="company-roles__title">Роли</h1>
      <div class="company-roles__tools">
        <n-button-group size="small" role="group" aria-label="Вид">
          <n-button
            :type="mode === 'list' ? 'primary' : 'default'"
            :secondary="mode === 'list'"
            :aria-pressed="mode === 'list'"
            @click="mode = 'list'"
          >
            Роли
          </n-button>
          <n-button
            :type="mode === 'matrix' ? 'primary' : 'default'"
            :secondary="mode === 'matrix'"
            :aria-pressed="mode === 'matrix'"
            @click="mode = 'matrix'"
          >
            Матрица
          </n-button>
        </n-button-group>
        <n-button v-if="canManageRoles" type="primary" size="small" @click="startCreating">
          <template #icon><n-icon :component="AddOutline" /></template>
          Новая роль
        </n-button>
      </div>
    </div>

    <p v-if="!canManageRoles" class="company-roles__note">
      Менять роли могут только те, у кого есть разрешение «Роли».
    </p>

    <role-matrix
      v-if="mode === 'matrix'"
      :roles="store.roles"
      :catalog="store.permissionCatalog"
      @select="selectRole"
    />

    <div v-else class="company-roles__body">
      <ul class="company-roles__list" aria-label="Роли компании">
        <li v-for="role in store.roles" :key="role.id">
          <button
            type="button"
            class="company-roles__item"
            :class="{ 'company-roles__item--active': !isCreating && role.id === selectedRoleId }"
            :aria-current="!isCreating && role.id === selectedRoleId ? 'true' : undefined"
            @click="selectRole(role.id)"
          >
            <span class="company-roles__badge" :style="{ background: role.color }">
              {{ role.name.charAt(0).toUpperCase() }}
            </span>
            <span class="company-roles__item-text">
              <span class="company-roles__item-name">{{ role.name }}</span>
              <span class="company-roles__item-usage">{{ usage(role) }}</span>
            </span>
          </button>
        </li>
      </ul>

      <section class="company-roles__panel">
        <n-spin :show="store.permissionCatalog.length === 0">
          <role-editor
            v-if="isCreating || selectedRole"
            :key="isCreating ? 'new' : selectedRole?.id"
            :role="isCreating ? null : selectedRole"
            :catalog="store.permissionCatalog"
            :can-edit="canManageRoles"
            :is-saving="isSaving"
            @save="handleSave"
            @remove="handleRemove"
          />
          <n-empty v-else description="Выберите роль" />
        </n-spin>
      </section>
    </div>
  </div>
  <p v-else class="company-roles__loading">Загрузка…</p>
</template>

<style scoped>
.company-roles {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.company-roles__back {
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

.company-roles__back:hover {
  color: var(--color-text);
}

.company-roles__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.company-roles__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.company-roles__tools {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.company-roles__note,
.company-roles__loading {
  margin: 0;
  color: var(--color-text-secondary);
}

.company-roles__body {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: var(--space-5);
  align-items: start;
}

.company-roles__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.company-roles__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.company-roles__item:hover {
  background: var(--color-bg-hover);
}

.company-roles__item--active {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
}

.company-roles__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: #fff;
  font-weight: 600;
  flex-shrink: 0;
}

.company-roles__item-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.company-roles__item-name {
  font-weight: 500;
}

.company-roles__item-usage {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.company-roles__panel {
  min-width: 0;
}

@media (max-width: 800px) {
  .company-roles__body {
    grid-template-columns: 1fr;
  }
}
</style>
