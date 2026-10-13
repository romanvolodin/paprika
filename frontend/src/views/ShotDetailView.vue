<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag, useDialog, useMessage } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import ShotFormModal, { type ShotFormValues } from '@/components/shots/ShotFormModal.vue'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'
import { useCurrentCompanyStore } from '@/stores/currentCompany'

const props = defineProps<{ companySlug: string; projectCode: string; shotName: string }>()

const router = useRouter()
const store = useShotDetailStore()
const currentCompany = useCurrentCompanyStore()
const message = useMessage()
const dialog = useDialog()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)

const isFormOpen = ref(false)
const isSaving = ref(false)

async function handleUpdate(values: ShotFormValues) {
  isSaving.value = true
  try {
    await store.updateShot({
      status_id: values.status_id,
      group_ids: values.group_ids,
      rec_timecode: values.rec_timecode,
      duration: values.duration,
    })
    isFormOpen.value = false
    message.success('Кадр обновлён.')
  } catch {
    message.error('Не удалось сохранить кадр. Проверьте введённые данные.')
  } finally {
    isSaving.value = false
  }
}

function confirmDelete() {
  if (!store.shot) return
  dialog.warning({
    title: 'Удалить кадр',
    content: `Удалить кадр ${store.shot.name}? Это действие необратимо.`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.deleteShot()
        message.success('Кадр удалён.')
        router.push({
          name: 'shot-list',
          params: { companySlug: props.companySlug, projectCode: props.projectCode },
        })
      } catch {
        message.error('Не удалось удалить кадр.')
      }
    },
  })
}

const status = computed(() => store.statuses.find((item) => item.id === store.shot?.status_id))
const shotGroups = computed(() =>
  store.groups.filter((group) => store.shot?.group_ids.includes(group.id)),
)

function formatFrames(value: number | null | undefined): string {
  return value == null ? '—' : String(value)
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
  <div class="shot-detail">
    <p v-if="store.state === 'not-found'" class="shot-detail__message">
      Кадр не найден или у вас нет к нему доступа.
    </p>

    <p v-else-if="store.state === 'error'" class="shot-detail__message">
      Не удалось загрузить кадр. Попробуйте обновить страницу.
    </p>

    <template v-else-if="store.shot && store.project">
      <button
        class="shot-detail__back"
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

      <div class="shot-detail__heading-row">
        <h1 class="shot-detail__title mono">{{ store.shot.name }}</h1>
        <span class="mono shot-detail__code">{{ store.project.code }}</span>
        <n-tag
          v-if="status"
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
        <div v-if="canWrite" class="shot-detail__actions">
          <n-button size="small" @click="isFormOpen = true">Изменить</n-button>
          <n-button size="small" type="error" secondary @click="confirmDelete">Удалить</n-button>
        </div>
      </div>

      <dl class="shot-detail__facts">
        <dt>Группы</dt>
        <dd>
          <span v-if="shotGroups.length === 0">—</span>
          <n-tag v-for="group in shotGroups" :key="group.id" size="small" round>
            {{ group.name }}
          </n-tag>
        </dd>
        <dt>Начало в монтаже, кадры</dt>
        <dd class="mono">{{ formatFrames(store.shot.rec_timecode) }}</dd>
        <dt>Длительность, кадры</dt>
        <dd class="mono">{{ formatFrames(store.shot.duration) }}</dd>
      </dl>

      <shot-form-modal
        v-model:show="isFormOpen"
        mode="edit"
        :shot="store.shot"
        :statuses="store.statuses"
        :groups="store.groups"
        :is-submitting="isSaving"
        @submit="handleUpdate"
      />

      <section class="shot-detail__section">
        <h2 class="shot-detail__heading">Версии</h2>
        <shot-versions-section :shot-id="store.shot.id" :can-write="canWrite" />
      </section>

      <section v-for="title in ['Задачи', 'Чат']" :key="title" class="shot-detail__section">
        <h2 class="shot-detail__heading">{{ title }}</h2>
        <p class="shot-detail__message">Пока не реализовано.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.shot-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 960px;
}

.shot-detail__message {
  color: var(--color-text-secondary);
}

.shot-detail__back {
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

.shot-detail__back:hover {
  color: var(--color-text);
}

.shot-detail__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.shot-detail__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.shot-detail__actions {
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
}

.shot-detail__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-detail__facts {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--space-2) var(--space-4);
  margin: 0;
}

.shot-detail__facts dt {
  color: var(--color-text-secondary);
}

.shot-detail__facts dd {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
  margin: 0;
}

.shot-detail__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 var(--space-2);
}
</style>
