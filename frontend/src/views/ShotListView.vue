<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
  NButton,
  NIcon,
  NInput,
  NPagination,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import ItemList from '@/components/common/ItemList.vue'
import ViewModeSwitch from '@/components/common/ViewModeSwitch.vue'
import ShotCard from '@/components/shots/ShotCard.vue'
import ShotFilterSection from '@/components/shots/ShotFilterSection.vue'
import ShotFormModal, { type ShotFormValues } from '@/components/shots/ShotFormModal.vue'
import ShotStatusTag from '@/components/shots/ShotStatusTag.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { PAGE_SIZE_OPTIONS } from '@/composables/usePageSize'
import { useViewMode } from '@/composables/useViewMode'
import { firstValidationMessage } from '@/utils/apiError'
import { useShotsStore } from '@/stores/shots'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import type { ShotOut } from '@/types/api'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const router = useRouter()
const shots = useShotsStore()
const currentCompany = useCurrentCompanyStore()

const message = useMessage()
const { project } = storeToRefs(shots)
const { can } = useProjectPermissions(project)

const viewMode = useViewMode('shots')
const pageSizeOptions = PAGE_SIZE_OPTIONS.map((size) => ({
  label: `${size} на странице`,
  value: size,
}))
const searchInput = ref('')
const isFormOpen = ref(false)
const isSaving = ref(false)

async function handleCreate(values: ShotFormValues) {
  isSaving.value = true
  try {
    await shots.createShot(values)
    isFormOpen.value = false
    message.success('Кадр создан.')
  } catch (error) {
    const isDuplicate = firstValidationMessage(error)?.includes('already exists')
    message.error(
      isDuplicate
        ? 'Кадр с таким именем уже есть в проекте.'
        : 'Не удалось создать кадр. Проверьте введённые данные.',
    )
  } finally {
    isSaving.value = false
  }
}

function goToImport() {
  router.push({
    name: 'shot-import',
    params: { companySlug: props.companySlug, projectCode: props.projectCode },
  })
}

const debouncedSearch = useDebounceFn((value: string) => {
  shots.setSearch(value)
}, 300)

function handleSearchInput(value: string) {
  searchInput.value = value
  debouncedSearch(value)
}

const statusFilterOptions = computed(() =>
  shots.statusOptions.map((status) => ({
    value: status.id,
    label: status.name,
    color: status.color,
  })),
)

const hasFilters = computed(
  () => shots.statusOptions.length > 0 || shots.assigneeOptions.length > 0,
)

function handleStatusFilter(selected: (number | 'none')[], inverted: boolean) {
  shots.setStatusFilter(selected as number[], inverted)
}

const statusById = computed(() => new Map(shots.statuses.map((status) => [status.id, status])))
const groupById = computed(() => new Map(shots.groups.map((group) => [group.id, group])))

function shotRoute(shot: ShotOut) {
  return {
    name: 'shot-detail',
    params: {
      companySlug: props.companySlug,
      projectCode: props.projectCode,
      shotName: shot.name,
    },
  }
}

function groupsOf(shot: ShotOut) {
  return shot.group_ids.flatMap((id) => {
    const group = groupById.value.get(id)
    return group ? [group] : []
  })
}

const columns = computed<DataTableColumns<ShotOut>>(() => [
  {
    title: 'Кадр',
    key: 'name',
    render: (shot) =>
      h(RouterLink, { class: 'mono', to: shotRoute(shot) }, { default: () => shot.name }),
  },
  {
    title: 'Группы',
    key: 'group_ids',
    render: (shot) =>
      h(
        'div',
        { class: 'shots-page__groups' },
        groupsOf(shot).map((group) =>
          h(NTag, { size: 'small', round: true }, { default: () => group.name }),
        ),
      ),
  },
  {
    title: 'Статус',
    key: 'status_id',
    width: 180,
    render: (shot) => {
      const status = statusById.value.get(shot.status_id)
      return status ? h(ShotStatusTag, { status }) : null
    },
  },
])

// The URL is the source of truth for which company and project are
// shown: an unknown slug is a 404, a known one becomes the active
// company (so the switcher in the sidebar agrees with the page).
watch(
  () => [props.companySlug, props.projectCode] as const,
  ([companySlug, projectCode]) => {
    const company = currentCompany.companies.find((candidate) => candidate.slug === companySlug)
    if (!company) {
      shots.state = 'not-found'
      return
    }
    if (currentCompany.currentCompanyId !== company.id) {
      currentCompany.selectCompany(company.id)
    }
    searchInput.value = ''
    shots.open(company, projectCode)
  },
  { immediate: true },
)
</script>

<template>
  <div class="shots-page">
    <p v-if="shots.state === 'not-found'" class="shots-page__message">
      Проект не найден или у вас нет к нему доступа.
    </p>

    <p v-else-if="shots.state === 'error'" class="shots-page__message">
      Не удалось загрузить кадры. Попробуйте обновить страницу.
    </p>

    <template v-else-if="shots.project">
      <div class="shots-page__heading-row">
        <h2 class="shots-page__title">Кадры</h2>
        <div
          v-if="can(PERMISSION.shotImport) || can(PERMISSION.shotCreate)"
          class="shots-page__actions"
        >
          <n-button v-if="can(PERMISSION.shotImport)" size="small" @click="goToImport">
            Импорт из таблицы
          </n-button>
          <n-button
            v-if="can(PERMISSION.shotCreate)"
            type="primary"
            size="small"
            @click="isFormOpen = true"
          >
            Новый кадр
          </n-button>
        </div>
      </div>

      <div class="shots-page__toolbar">
        <n-input
          :value="searchInput"
          placeholder="Поиск по названию"
          clearable
          style="max-width: 320px"
          @update:value="handleSearchInput"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <view-mode-switch v-model="viewMode" />
      </div>

      <div class="shots-page__body">
        <div class="shots-page__main">
          <item-list
            :items="shots.items"
            :columns="columns"
            :mode="viewMode"
            :loading="shots.isLoading"
            :row-key="(shot: ShotOut) => shot.id"
          >
            <template #card="{ item }">
              <shot-card
                :shot="item"
                :status="statusById.get(item.status_id)"
                :groups="groupsOf(item)"
                :to="shotRoute(item)"
              />
            </template>
          </item-list>

          <div class="shots-page__pagination">
            <n-pagination
              :page="shots.page"
              :page-size="shots.pageSize"
              :item-count="shots.total"
              :page-sizes="pageSizeOptions"
              show-size-picker
              @update:page="shots.setPage"
              @update:page-size="shots.setPageSize"
            />
          </div>
        </div>

        <aside v-if="hasFilters" class="shots-page__filters">
          <shot-filter-section
            v-if="shots.statusOptions.length > 0"
            title="Статус"
            :options="statusFilterOptions"
            :selected="shots.statusSelected"
            :inverted="shots.statusInverted"
            @change="handleStatusFilter"
          />
          <shot-filter-section
            v-if="shots.assigneeOptions.length > 0"
            title="Исполнитель"
            :options="shots.assigneeOptions"
            :selected="shots.assigneeSelected"
            :inverted="shots.assigneeInverted"
            @change="shots.setAssigneeFilter"
          />
        </aside>
      </div>

      <shot-form-modal
        v-model:show="isFormOpen"
        mode="create"
        :statuses="shots.statuses"
        :groups="shots.groups"
        :is-submitting="isSaving"
        @submit="handleCreate"
      />
    </template>
  </div>
</template>

<style scoped>
.shots-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 1200px;
}

.shots-page__body {
  display: flex;
  align-items: flex-start;
  gap: var(--space-6, 32px);
}

.shots-page__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.shots-page__filters {
  flex: 0 0 220px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5, 24px);
}

.shots-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.shots-page__message {
  color: var(--color-text-secondary);
}

.shots-page__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.shots-page__title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.shots-page__actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-2);
}

.shots-page__groups {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}

.shots-page__pagination {
  display: flex;
  justify-content: flex-end;
}
</style>
