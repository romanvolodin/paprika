<script setup lang="ts">
import { computed, h, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { NSelect, NTag, useMessage, type SelectOption } from 'naive-ui'
import { storeToRefs } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'
import { useCurrentCompanyStore } from '@/stores/currentCompany'

const props = defineProps<{ companySlug: string; projectCode: string; shotName: string }>()

const store = useShotDetailStore()
const currentCompany = useCurrentCompanyStore()
const message = useMessage()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)

const routeParams = computed(() => ({
  companySlug: props.companySlug,
  projectCode: props.projectCode,
  shotName: props.shotName,
}))

const status = computed(() => store.statuses.find((item) => item.id === store.shot?.status_id))
const statusOptions = computed(() =>
  store.statuses.map((item) => ({ label: item.name, value: item.id, color: item.color })),
)

function renderStatusLabel(option: SelectOption) {
  return h('span', { class: 'shot-page__status-label' }, [
    h('span', {
      class: 'shot-page__status-dot',
      style: { backgroundColor: String(option.color) },
    }),
    String(option.label),
  ])
}

async function handleStatusChange(statusId: number) {
  try {
    await store.updateShot({ status_id: statusId })
  } catch {
    message.error('Не удалось изменить статус.')
  }
}

// Same contract as the shot list: the URL decides the company and
// project, and an unknown company slug is a 404.
watch(
  () => [props.companySlug, props.projectCode, props.shotName] as const,
  ([companySlug, projectCode, shotName]) => {
    const company = currentCompany.companies.find((candidate) => candidate.slug === companySlug)
    if (!company) {
      store.state = 'not-found'
      return
    }
    if (currentCompany.currentCompanyId !== company.id) {
      currentCompany.selectCompany(company.id)
    }
    store.open(company, projectCode, shotName)
  },
  { immediate: true },
)
</script>

<template>
  <div class="shot-page">
    <p v-if="store.state === 'not-found'" class="shot-page__message">
      Кадр не найден или у вас нет к нему доступа.
    </p>

    <p v-else-if="store.state === 'error'" class="shot-page__message">
      Не удалось загрузить кадр. Попробуйте обновить страницу.
    </p>

    <template v-else-if="store.shot && store.project">
      <header class="shot-page__header">
        <RouterLink
          class="shot-page__crumb mono"
          :to="{ name: 'shot-list', params: { companySlug, projectCode } }"
          :title="store.project.name"
        >
          {{ store.project.code }}
        </RouterLink>
        <span class="shot-page__separator" aria-hidden="true">/</span>
        <h1 class="shot-page__title mono">{{ store.shot.name }}</h1>
        <n-select
          v-if="canWrite"
          class="shot-page__status-select"
          size="small"
          :value="store.shot.status_id"
          :options="statusOptions"
          :render-label="renderStatusLabel"
          @update:value="handleStatusChange"
        />
        <n-tag
          v-else-if="status"
          size="small"
          round
          :color="{
            color: `${status.color}26`,
            borderColor: status.color,
            textColor: status.color,
          }"
        >
          {{ status.name }}
        </n-tag>

        <nav class="shot-page__nav" aria-label="Разделы кадра">
          <RouterLink
            class="shot-page__link"
            exact-active-class="shot-page__link--active"
            :to="{ name: 'shot-detail', params: routeParams }"
          >
            Просмотр
          </RouterLink>
          <RouterLink
            class="shot-page__link"
            exact-active-class="shot-page__link--active"
            :to="{ name: 'shot-tasks', params: routeParams }"
          >
            Задачи
          </RouterLink>
          <RouterLink
            class="shot-page__link"
            exact-active-class="shot-page__link--active"
            :to="{ name: 'shot-versions', params: routeParams }"
          >
            Версии
          </RouterLink>
          <RouterLink
            class="shot-page__link"
            exact-active-class="shot-page__link--active"
            :to="{ name: 'shot-settings', params: routeParams }"
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
.shot-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
}

.shot-page__message {
  color: var(--color-text-secondary);
}

.shot-page__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  min-height: 44px;
  border-bottom: 1px solid var(--color-border);
}

.shot-page__crumb {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  text-decoration: none;
}

.shot-page__crumb:hover {
  color: var(--color-text);
}

.shot-page__separator {
  margin-left: calc(var(--space-1) * -1);
  color: var(--color-text-secondary);
}

.shot-page__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.shot-page__status-select {
  width: 180px;
}

.shot-page__nav {
  display: flex;
  align-self: stretch;
  gap: var(--space-1);
  margin-left: var(--space-3);
}

.shot-page__link {
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  margin-bottom: -1px;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  text-decoration: none;
}

.shot-page__link:hover {
  color: var(--color-text);
}

.shot-page__link--active {
  color: var(--color-text);
  font-weight: 600;
  border-bottom-color: var(--color-accent);
}
</style>

<style>
.shot-page__status-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.shot-page__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
</style>
