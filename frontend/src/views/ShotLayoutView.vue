<script setup lang="ts">
import { computed, h, watch } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { NIcon, NSelect, NTag, useMessage, type SelectOption } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'
import { useCurrentCompanyStore } from '@/stores/currentCompany'

const props = defineProps<{ companySlug: string; projectCode: string; shotName: string }>()

const router = useRouter()
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
        <button
          class="shot-page__back"
          type="button"
          @click="
            router.push({
              name: 'shot-list',
              params: { companySlug: props.companySlug, projectCode: props.projectCode },
            })
          "
        >
          <n-icon :component="ArrowBackOutline" />
          К списку кадров
        </button>

        <div class="shot-page__heading-row">
          <h1 class="shot-page__title mono">{{ store.shot.name }}</h1>
          <span class="mono shot-page__code">{{ store.project.code }}</span>
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
        </div>

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
  flex-direction: column;
  gap: var(--space-5);
}

.shot-page__message {
  color: var(--color-text-secondary);
}

.shot-page__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 960px;
}

.shot-page__back {
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

.shot-page__back:hover {
  color: var(--color-text);
}

.shot-page__heading-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.shot-page__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.shot-page__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-page__status-select {
  width: 180px;
}

.shot-page__nav {
  display: flex;
  gap: var(--space-1);
  border-bottom: 1px solid var(--color-border);
}

.shot-page__link {
  padding: var(--space-2) var(--space-3);
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
