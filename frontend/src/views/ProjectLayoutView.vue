<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import { useProjectPageStore } from '@/stores/projectPage'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const route = useRoute()
const store = useProjectPageStore()
const currentCompany = useCurrentCompanyStore()
const { members } = storeToRefs(store)
const { canManageProject } = useProjectPermissions(members)

// A link is highlighted by section, not by router-link matching: the
// shot page and the import page are siblings of the shot list in the
// route tree, yet they belong to the "Кадры" section.
const SECTION_ROUTES = {
  shots: [
    'shot-list',
    'shot-import',
    'shot-detail',
    'shot-tasks',
    'shot-versions',
    'shot-settings',
  ],
  tasks: ['project-tasks'],
  groups: ['project-groups'],
  settings: ['project-settings'],
} as const

type Section = keyof typeof SECTION_ROUTES

function isActive(section: Section): boolean {
  return (SECTION_ROUTES[section] as readonly unknown[]).includes(route.name)
}

const routeParams = computed(() => ({
  companySlug: props.companySlug,
  projectCode: props.projectCode,
}))

// The URL decides which company and project are shown: an unknown
// slug is a 404, a known one becomes the active company (so the
// switcher in the sidebar agrees with the page).
watch(
  () => [props.companySlug, props.projectCode] as const,
  ([companySlug, projectCode]) => {
    const company = currentCompany.companies.find((candidate) => candidate.slug === companySlug)
    if (!company) {
      store.setNotFound()
      return
    }
    if (currentCompany.currentCompanyId !== company.id) {
      currentCompany.selectCompany(company.id)
    }
    store.open(company, projectCode)
  },
  { immediate: true },
)
</script>

<template>
  <div class="project-page">
    <p v-if="store.state === 'not-found'" class="project-page__message">
      Проект не найден или у вас нет к нему доступа.
    </p>

    <p v-else-if="store.state === 'error'" class="project-page__message">
      Не удалось загрузить проект. Попробуйте обновить страницу.
    </p>

    <template v-else-if="store.project">
      <header class="project-page__header">
        <div class="project-page__heading-row">
          <h1 class="project-page__title">{{ store.project.name }}</h1>
          <span class="mono project-page__code">{{ store.project.code }}</span>
        </div>

        <nav class="project-page__nav" aria-label="Разделы проекта">
          <div class="project-page__nav-group">
            <RouterLink
              class="project-page__link"
              :class="{ 'project-page__link--active': isActive('shots') }"
              :to="{ name: 'shot-list', params: routeParams }"
            >
              Кадры
            </RouterLink>
            <RouterLink
              class="project-page__link"
              :class="{ 'project-page__link--active': isActive('tasks') }"
              :to="{ name: 'project-tasks', params: routeParams }"
            >
              Задачи
            </RouterLink>
            <RouterLink
              class="project-page__link"
              :class="{ 'project-page__link--active': isActive('groups') }"
              :to="{ name: 'project-groups', params: routeParams }"
            >
              Группы
            </RouterLink>
          </div>
          <RouterLink
            v-if="canManageProject"
            class="project-page__link"
            :class="{ 'project-page__link--active': isActive('settings') }"
            :to="{ name: 'project-settings', params: routeParams }"
          >
            Настройки
          </RouterLink>
        </nav>
      </header>

      <RouterView />
    </template>
  </div>
</template>

<style scoped>
.project-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}

.project-page__message {
  color: var(--color-text-secondary);
}

.project-page__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 960px;
}

.project-page__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.project-page__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.project-page__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-page__nav {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid var(--color-border);
}

.project-page__nav-group {
  display: flex;
  gap: var(--space-1);
}

.project-page__link {
  padding: var(--space-2) var(--space-3);
  margin-bottom: -1px;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  text-decoration: none;
}

.project-page__link:hover {
  color: var(--color-text);
}

.project-page__link--active {
  color: var(--color-text);
  font-weight: 600;
  border-bottom-color: var(--color-accent);
}
</style>
