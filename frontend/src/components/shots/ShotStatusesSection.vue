<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { isAxiosError } from 'axios'
import {
  NButton,
  NColorPicker,
  NDataTable,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NInputNumber,
  NModal,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useShotStatusesStore } from '@/stores/shotStatuses'
import { firstValidationMessage } from '@/utils/apiError'
import type { ShotStatusOut } from '@/types/api'

const props = defineProps<{ companyId: number; canEdit: boolean }>()

const store = useShotStatusesStore()
const message = useMessage()
const dialog = useDialog()

const formRef = ref<FormInst | null>(null)
const isFormOpen = ref(false)
const editingStatus = ref<ShotStatusOut | null>(null)
const isSaving = ref(false)

const name = ref('')
const color = ref('#888888')
const order = ref<number | null>(null)
const isDefault = ref(false)

watch(
  () => props.companyId,
  (companyId) => store.fetch(companyId),
  { immediate: true },
)

function openCreate() {
  editingStatus.value = null
  name.value = ''
  color.value = '#888888'
  order.value = null
  isDefault.value = false
  isFormOpen.value = true
}

function openEdit(status: ShotStatusOut) {
  editingStatus.value = status
  name.value = status.name
  color.value = status.color
  order.value = status.order
  isDefault.value = status.is_default
  isFormOpen.value = true
}

const rules: FormRules = {
  name: [{ required: true, message: 'Введите название', trigger: 'blur' }],
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  const input = {
    name: name.value.trim(),
    color: color.value,
    order: order.value,
    is_default: isDefault.value,
  }
  isSaving.value = true
  try {
    if (editingStatus.value) {
      await store.update(props.companyId, editingStatus.value.id, input)
    } else {
      await store.create(props.companyId, input)
    }
    isFormOpen.value = false
  } catch (error) {
    message.error(
      firstValidationMessage(error)?.includes('already exists')
        ? 'Статус с таким названием уже есть в компании.'
        : 'Не удалось сохранить статус. Проверьте введённые данные.',
    )
  } finally {
    isSaving.value = false
  }
}

function confirmDelete(status: ShotStatusOut) {
  dialog.warning({
    title: 'Удалить статус',
    content: `Удалить статус «${status.name}»?`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(props.companyId, status.id)
        message.success('Статус удалён.')
      } catch (error) {
        message.error(
          isAxiosError(error) && error.response?.status === 400
            ? 'Статус используется кадрами, удалить его нельзя.'
            : 'Не удалось удалить статус.',
        )
      }
    },
  })
}

const columns = computed<DataTableColumns<ShotStatusOut>>(() => [
  {
    title: 'Название',
    key: 'name',
    render: (status) =>
      h(
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
      ),
  },
  {
    title: 'Порядок',
    key: 'order',
    width: 110,
    render: (status) => (status.order === null ? '—' : String(status.order)),
  },
  {
    title: 'По умолчанию',
    key: 'is_default',
    width: 140,
    render: (status) => (status.is_default ? 'Да' : ''),
  },
  ...(props.canEdit
    ? [
        {
          title: '',
          key: 'actions',
          width: 200,
          render: (status: ShotStatusOut) =>
            h('div', { class: 'shot-statuses__actions' }, [
              h(
                NButton,
                { size: 'small', quaternary: true, onClick: () => openEdit(status) },
                { default: () => 'Изменить' },
              ),
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'error',
                  onClick: () => confirmDelete(status),
                },
                { default: () => 'Удалить' },
              ),
            ]),
        },
      ]
    : []),
])
</script>

<template>
  <div class="shot-statuses">
    <n-data-table
      :columns="columns"
      :data="store.items"
      :loading="store.isLoading"
      :bordered="false"
      :row-key="(row: ShotStatusOut) => row.id"
    />

    <div v-if="canEdit">
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        Добавить статус
      </n-button>
    </div>

    <n-modal
      v-model:show="isFormOpen"
      preset="card"
      :title="editingStatus ? 'Изменить статус' : 'Новый статус'"
      style="max-width: 440px"
    >
      <n-form
        ref="formRef"
        :model="{ name }"
        :rules="rules"
        label-placement="top"
        @submit.prevent="handleSave"
      >
        <n-form-item label="Название" path="name">
          <n-input v-model:value="name" />
        </n-form-item>
        <n-form-item label="Цвет">
          <n-color-picker v-model:value="color" :modes="['hex']" :show-alpha="false" />
        </n-form-item>
        <n-form-item label="Порядок в процессе (пусто — вне основного процесса)">
          <n-input-number v-model:value="order" :precision="0" clearable />
        </n-form-item>
        <n-form-item label="Статус по умолчанию для новых кадров">
          <n-switch v-model:value="isDefault" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="shot-statuses__modal-actions">
          <n-button :disabled="isSaving" @click="isFormOpen = false">Отмена</n-button>
          <n-button type="primary" :loading="isSaving" @click="handleSave">Сохранить</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.shot-statuses {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-statuses__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

<style>
.shot-statuses__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1, 4px);
}
</style>
