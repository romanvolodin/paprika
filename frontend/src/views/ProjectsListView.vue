<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter, type RouteLocationRaw } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
  NButton,
  NIcon,
  NInput,
  NPagination,
  NRadioButton,
  NRadioGroup,
  NTag,
  type DataTableColumns,
} from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import ItemList from '@/components/common/ItemList.vue'
import ViewModeSwitch from '@/components/common/ViewModeSwitch.vue'
import ProjectCard from '@/components/projects/ProjectCard.vue'
import {
  useProjectStatusFilter,
  type ProjectStatusFilter,
} from '@/composables/useProjectStatusFilter'
import { useViewMode } from '@/composables/useViewMode'
import { useProjectsStore } from '@/stores/projects'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import type { ProjectOut } from '@/types/api'

const router = useRouter()
const projects = useProjectsStore()
const currentCompany = useCurrentCompanyStore()

const viewMode = useViewMode('projects')
const statusFilter = useProjectStatusFilter('projects')

const searchInput = ref('')

const debouncedSearch = useDebounceFn((value: string) => {
  projects.setSearch(value)
}, 300)

function handleSearchInput(value: string) {
  searchInput.value = value
  debouncedSearch(value)
}

function handleStatusFilterChange(value: string | number | boolean) {
  statusFilter.value = value as ProjectStatusFilter
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('ru-RU')
}

const companySlugById = computed(
  () => new Map(currentCompany.companies.map((company) => [company.id, company.slug])),
)

function projectRoute(project: ProjectOut): RouteLocationRaw | null {
  const companySlug = companySlugById.value.get(project.company_id)
  if (!companySlug) return null
  return { name: 'project-home', params: { companySlug, projectCode: project.code } }
}

const columns: DataTableColumns<ProjectOut> = [
  {
    title: 'Название',
    key: 'name',
    render: (project) => {
      const to = projectRoute(project)
      if (!to) return project.name
      return h(RouterLink, { to }, { default: () => project.name })
    },
  },
  {
    title: 'Код',
    key: 'code',
    width: 120,
    render: (project) => h('span', { class: 'mono' }, project.code),
  },
  {
    title: 'Статус',
    key: 'is_active',
    width: 120,
    render: (project) =>
      h(
        NTag,
        { type: project.is_active ? 'success' : 'default', size: 'small', round: true },
        { default: () => (project.is_active ? 'Активен' : 'Архив') },
      ),
  },
  {
    title: 'Создан',
    key: 'created_at',
    width: 140,
    render: (project) => formatDate(project.created_at),
  },
]

const filteredItems = computed(() => {
  if (statusFilter.value === 'active') {
    return projects.items.filter((project) => project.is_active)
  }
  if (statusFilter.value === 'archived') {
    return projects.items.filter((project) => !project.is_active)
  }
  return projects.items
})

function fetchForCurrentCompany() {
  if (currentCompany.currentCompanyId !== null) {
    projects.fetchProjects(currentCompany.currentCompanyId)
  }
}

onMounted(fetchForCurrentCompany)

// The active company can change at any time via the switcher in the
// sidebar, without a route change - so the list needs to react on its
// own rather than only fetching once on mount.
watch(() => currentCompany.currentCompanyId, fetchForCurrentCompany)
</script>

<template>
  <div class="projects-page">
    <template v-if="currentCompany.companies.length === 0">
      <p class="projects-page__empty">У вас пока нет ни одной компании.</p>
    </template>

    <template v-else-if="currentCompany.currentCompanyId === null">
      <p class="projects-page__empty">
        Выберите компанию в переключателе слева, чтобы увидеть её проекты.
      </p>
    </template>

    <template v-else>
      <div class="projects-page__toolbar">
        <n-input
          :value="searchInput"
          placeholder="Поиск по названию"
          clearable
          style="max-width: 320px"
          @update:value="handleSearchInput"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>

        <n-radio-group
          :value="statusFilter"
          name="project-status-filter"
          size="small"
          @update:value="handleStatusFilterChange"
        >
          <n-radio-button value="all">Все</n-radio-button>
          <n-radio-button value="active">Активные</n-radio-button>
          <n-radio-button value="archived">Архив</n-radio-button>
        </n-radio-group>

        <div class="projects-page__toolbar-actions">
          <view-mode-switch v-model="viewMode" />
          <n-button type="primary" @click="router.push({ name: 'project-create' })">
            <template #icon><n-icon :component="AddOutline" /></template>
            Новый проект
          </n-button>
        </div>
      </div>

      <item-list
        :items="filteredItems"
        :columns="columns"
        :mode="viewMode"
        :loading="projects.isLoading"
        :row-key="(project: ProjectOut) => project.id"
        class="projects-page__list"
      >
        <template #card="{ item }">
          <project-card :project="item" :to="projectRoute(item) ?? undefined" />
        </template>
      </item-list>

      <div class="projects-page__pagination">
        <n-pagination
          :page="projects.page"
          :page-size="projects.pageSize"
          :item-count="projects.total"
          @update:page="projects.setPage"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.projects-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 960px;
}

.projects-page__empty {
  color: var(--color-text-secondary);
}

.projects-page__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  justify-content: space-between;
  flex-wrap: wrap;
}

.projects-page__toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.projects-page__pagination {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .projects-page__list {
    font-size: var(--text-sm, 13px);
  }
}
</style>
