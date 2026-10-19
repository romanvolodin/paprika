<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
  NButton,
  NDataTable,
  NIcon,
  NInput,
  NPagination,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { ArrowBackOutline, SearchOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import ShotFormModal, { type ShotFormValues } from '@/components/shots/ShotFormModal.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { firstValidationMessage } from '@/utils/apiError'
import { useShotsStore } from '@/stores/shots'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import type { ShotOut } from '@/types/api'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const router = useRouter()
const shots = useShotsStore()
const currentCompany = useCurrentCompanyStore()

const message = useMessage()
const { members } = storeToRefs(shots)
const { canWrite } = useProjectPermissions(members)

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

const statusById = computed(() => new Map(shots.statuses.map((status) => [status.id, status])))
const groupById = computed(() => new Map(shots.groups.map((group) => [group.id, group])))

const columns = computed<DataTableColumns<ShotOut>>(() => [
  {
    title: 'Кадр',
    key: 'name',
    render: (shot) =>
      h(
        RouterLink,
        {
          class: 'mono',
          to: {
            name: 'shot-detail',
            params: {
              companySlug: props.companySlug,
              projectCode: props.projectCode,
              shotName: shot.name,
            },
          },
        },
        { default: () => shot.name },
      ),
  },
  {
    title: 'Группы',
    key: 'group_ids',
    render: (shot) =>
      h(
        'div',
        { class: 'shots-page__groups' },
        shot.group_ids.flatMap((id) => {
          const group = groupById.value.get(id)
          return group
            ? [h(NTag, { size: 'small', round: true }, { default: () => group.name })]
            : []
        }),
      ),
  },
  {
    title: 'Статус',
    key: 'status_id',
    width: 180,
    render: (shot) => {
      const status = statusById.value.get(shot.status_id)
      if (!status) return null
      return h(
        NTag,
        {
          size: 'small',
          round: true,
          color: {
            color: `${status.color}26`,
            borderColor: status.color,
            textColor: status.color,
          },
        },
        { default: () => status.name },
      )
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
      <button
        class="shots-page__back"
        type="button"
        @click="router.push({ name: 'project-detail', params: { id: shots.project.id } })"
      >
        <n-icon :component="ArrowBackOutline" />
        К проекту
      </button>

      <div class="shots-page__heading-row">
        <h1 class="shots-page__title">Кадры</h1>
        <span class="mono shots-page__code">{{ shots.project.code }}</span>
        <div v-if="canWrite" class="shots-page__actions">
          <n-button size="small" @click="goToImport">Импорт из таблицы</n-button>
          <n-button type="primary" size="small" @click="isFormOpen = true">Новый кадр</n-button>
        </div>
      </div>

      <n-input
        :value="searchInput"
        placeholder="Поиск по названию"
        clearable
        style="max-width: 320px"
        @update:value="handleSearchInput"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>

      <n-data-table
        :columns="columns"
        :data="shots.items"
        :loading="shots.isLoading"
        :bordered="false"
        :row-key="(row: ShotOut) => row.id"
      />

      <shot-form-modal
        v-model:show="isFormOpen"
        mode="create"
        :statuses="shots.statuses"
        :groups="shots.groups"
        :is-submitting="isSaving"
        @submit="handleCreate"
      />

      <div class="shots-page__pagination">
        <n-pagination
          :page="shots.page"
          :page-size="shots.pageSize"
          :item-count="shots.total"
          @update:page="shots.setPage"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.shots-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 960px;
}

.shots-page__message {
  color: var(--color-text-secondary);
}

.shots-page__back {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0;
  border: none;
  background: none;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  cursor: pointer;
}

.shots-page__back:hover {
  color: var(--color-text);
}

.shots-page__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.shots-page__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.shots-page__actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-2);
}

.shots-page__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
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
