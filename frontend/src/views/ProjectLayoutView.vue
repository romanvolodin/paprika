<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import { useProjectPageStore } from '@/stores/projectPage'
import AppHeaderContent from '@/components/layout/AppHeaderContent.vue'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const route = useRoute()
const store = useProjectPageStore()
const currentCompany = useCurrentCompanyStore()
const { project } = storeToRefs(store)
const { canOpenSettings } = useProjectPermissions(project)

// A link is highlighted by section, not by router-link matching: the
// import page is a sibling of the shot list in the route tree, yet it
// belongs to the "Кадры" section.
const SECTION_ROUTES = {
  feed: ['project-feed'],
  shots: ['shot-list', 'shot-import'],
  tasks: ['project-tasks'],
  groups: ['project-groups'],
  settings: ['project-settings'],
} as const

type Section = keyof typeof SECTION_ROUTES

function isActive(section: Section): boolean {
  return (SECTION_ROUTES[section] as readonly unknown[]).includes(route.name)
}

// The shot page has its own header that already carries the way back
// to the project, so the project header is not shown there.
const SHOT_PAGE_ROUTES = [
  'shot-detail',
  'shot-tasks',
  'shot-versions',
  'shot-upload',
  'shot-settings',
]
const hasProjectHeader = computed(() => !SHOT_PAGE_ROUTES.includes(String(route.name)))

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
      <AppHeaderContent v-if="hasProjectHeader">
        <div class="project-page__title-block">
          <h1 class="project-page__title">{{ store.project.name }}</h1>
          <span class="mono project-page__code">{{ store.project.code }}</span>
        </div>

        <nav class="project-page__nav" aria-label="Разделы проекта">
          <RouterLink
            class="project-page__link"
            :class="{ 'project-page__link--active': isActive('feed') }"
            :to="{ name: 'project-feed', params: routeParams }"
          >
            Лента
          </RouterLink>
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
          <RouterLink
            v-if="canOpenSettings"
            class="project-page__link"
            :class="{ 'project-page__link--active': isActive('settings') }"
            :to="{ name: 'project-settings', params: routeParams }"
          >
            Настройки
          </RouterLink>
        </nav>
      </AppHeaderContent>

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

.project-page__title-block {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  white-space: nowrap;
}

.project-page__title {
  max-width: 240px;
  overflow: hidden;
  font-size: 1.125rem;
  font-weight: 600;
  text-overflow: ellipsis;
  margin: 0;
}

.project-page__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-page__nav {
  display: flex;
  align-self: stretch;
  gap: var(--space-1);
  margin-left: var(--space-3);
}

.project-page__link {
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  white-space: nowrap;
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
