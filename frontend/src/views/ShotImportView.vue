<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NSpin, useMessage } from 'naive-ui'
import { ArrowBackOutline, DocumentTextOutline } from '@vicons/ionicons5'
import { storeToRefs } from 'pinia'
import ShotImportPreview from '@/components/shots/ShotImportPreview.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import { useShotImportStore } from '@/stores/shotImport'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const router = useRouter()
const message = useMessage()
const currentCompany = useCurrentCompanyStore()
const store = useShotImportStore()

const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)
const canImport = computed(() => can(PERMISSION.shotImport))

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

// The URL decides which company and project the import is for - same
// rule as on the shot list.
watch(
  () => [props.companySlug, props.projectCode] as const,
  ([companySlug, projectCode]) => {
    const company = currentCompany.companies.find((candidate) => candidate.slug === companySlug)
    if (!company) {
      store.state = 'not-found'
      return
    }
    if (currentCompany.currentCompanyId !== company.id) {
      currentCompany.selectCompany(company.id)
    }
    store.open(company, projectCode)
  },
  { immediate: true },
)

function goToShots() {
  router.push({
    name: 'shot-list',
    params: { companySlug: props.companySlug, projectCode: props.projectCode },
  })
}

async function handleFile(file: File | undefined) {
  if (!file) return
  try {
    await store.loadFile(file)
    if (store.hasFile && store.rows.length === 0) {
      message.warning('В таблице нет ни одной непустой строки.')
    }
  } catch {
    message.error('Не удалось прочитать файл. Поддерживаются xlsx, xls, ods и csv.')
  }
}

function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  handleFile(input.files?.[0])
  input.value = ''
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  handleFile(event.dataTransfer?.files?.[0])
}

function handleChangeFile() {
  store.reset()
}

async function handleSubmit() {
  try {
    const result = await store.submit()
    if (!result) return
    message.success(`Создано кадров: ${result.shots_created}.`)
    goToShots()
  } catch {
    message.error(
      store.problems.size > 0 || store.generalProblems.length > 0
        ? 'Кадры не созданы: исправьте отмеченные строки.'
        : 'Не удалось создать кадры. Попробуйте ещё раз.',
    )
  }
}
</script>

<template>
  <div class="import-page">
    <p v-if="store.state === 'not-found'" class="import-page__message">
      Проект не найден или у вас нет к нему доступа.
    </p>

    <p v-else-if="store.state === 'error'" class="import-page__message">
      Не удалось загрузить проект. Попробуйте обновить страницу.
    </p>

    <n-spin v-else-if="store.state === 'loading'" class="import-page__spin" />

    <template v-else-if="store.project">
      <button class="import-page__back" type="button" @click="goToShots">
        <n-icon :component="ArrowBackOutline" />
        К кадрам
      </button>

      <div class="import-page__heading-row">
        <h1 class="import-page__title">Импорт кадров из таблицы</h1>
        <span class="mono import-page__code">{{ store.project.code }}</span>
      </div>

      <p v-if="!canImport" class="import-page__message">
        Ваша роль в этом проекте не позволяет создавать кадры.
      </p>

      <shot-import-preview
        v-else-if="store.hasFile"
        @submit="handleSubmit"
        @change-file="handleChangeFile"
      />

      <div
        v-else
        class="import-page__drop"
        :class="{ 'import-page__drop--active': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <n-icon :component="DocumentTextOutline" size="32" />
        <p>Перетащите сюда таблицу или выберите файл (xlsx, xls, ods, csv).</p>
        <n-button type="primary" :loading="store.isReadingFile" @click="fileInput?.click()">
          Выбрать файл
        </n-button>
        <input
          ref="fileInput"
          class="import-page__input"
          type="file"
          accept=".xlsx,.xls,.ods,.csv,.tsv"
          data-testid="file-input"
          @change="handleFileInput"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.import-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.import-page__message {
  color: var(--color-text-secondary);
}

.import-page__spin {
  align-self: flex-start;
}

.import-page__back {
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

.import-page__back:hover {
  color: var(--color-text);
}

.import-page__heading-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.import-page__title {
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}

.import-page__code {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.import-page__drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  max-width: 560px;
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-align: center;
}

.import-page__drop--active {
  border-color: var(--color-accent);
  background: var(--color-accent-soft);
}

.import-page__drop p {
  margin: 0;
}

.import-page__input {
  display: none;
}
</style>
