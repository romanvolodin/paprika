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
  NModal,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useTaskTypesStore } from '@/stores/taskTypes'
import { firstDetailMessage } from '@/utils/apiError'
import { tagColor } from '@/utils/color'
import type { TaskTypeOut } from '@/types/api'

const props = defineProps<{ companyId: number; canEdit: boolean }>()

const store = useTaskTypesStore()
const message = useMessage()
const dialog = useDialog()

const formRef = ref<FormInst | null>(null)
const isFormOpen = ref(false)
const editingType = ref<TaskTypeOut | null>(null)
const isSaving = ref(false)

const name = ref('')
const abbreviation = ref('')
const color = ref('#888888')

watch(
  () => props.companyId,
  (companyId) => store.fetch(companyId),
  { immediate: true },
)

function openCreate() {
  editingType.value = null
  name.value = ''
  abbreviation.value = ''
  color.value = '#888888'
  isFormOpen.value = true
}

function openEdit(type: TaskTypeOut) {
  editingType.value = type
  name.value = type.name
  abbreviation.value = type.abbreviation
  color.value = type.color
  isFormOpen.value = true
}

// Mirrors the backend rule: the abbreviation becomes the prefix of task codes.
const ABBREVIATION_PATTERN = /^[A-Z0-9]{2,5}$/

const rules: FormRules = {
  name: [{ required: true, message: 'Введите название', trigger: 'blur' }],
  abbreviation: [
    { required: true, message: 'Введите аббревиатуру', trigger: 'blur' },
    {
      validator: (_rule, value: string) => !value || ABBREVIATION_PATTERN.test(value),
      message: '2–5 заглавных латинских букв или цифр',
      trigger: ['blur', 'input'],
    },
  ],
}

function describeSaveError(error: unknown): string {
  const detail = firstDetailMessage(error) ?? ''
  if (isAxiosError(error) && error.response?.status === 409) {
    return detail.includes('abbreviation')
      ? 'Тип с такой аббревиатурой уже есть в компании.'
      : 'Тип с таким названием уже есть в компании.'
  }
  return 'Не удалось сохранить тип. Проверьте введённые данные.'
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  const input = {
    name: name.value.trim(),
    abbreviation: abbreviation.value,
    color: color.value,
  }
  isSaving.value = true
  try {
    if (editingType.value) {
      await store.update(props.companyId, editingType.value.id, input)
    } else {
      await store.create(props.companyId, input)
    }
    isFormOpen.value = false
  } catch (error) {
    message.error(describeSaveError(error))
  } finally {
    isSaving.value = false
  }
}

function confirmDelete(type: TaskTypeOut) {
  dialog.warning({
    title: 'Удалить тип задач',
    content: `Удалить тип «${type.name}»?`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(props.companyId, type.id)
        message.success('Тип удалён.')
      } catch (error) {
        message.error(
          isAxiosError(error) && error.response?.status === 409
            ? 'Тип используется задачами, удалить его нельзя.'
            : 'Не удалось удалить тип.',
        )
      }
    },
  })
}

const columns = computed<DataTableColumns<TaskTypeOut>>(() => [
  {
    title: 'Название',
    key: 'name',
    render: (type) =>
      h(
        NTag,
        { size: 'small', round: true, color: tagColor(type.color) },
        { default: () => type.name },
      ),
  },
  {
    title: 'Аббревиатура',
    key: 'abbreviation',
    width: 150,
    render: (type) => h('span', { class: 'mono' }, type.abbreviation),
  },
  ...(props.canEdit
    ? [
        {
          title: '',
          key: 'actions',
          width: 200,
          render: (type: TaskTypeOut) =>
            h('div', { class: 'task-types__actions' }, [
              h(
                NButton,
                { size: 'small', quaternary: true, onClick: () => openEdit(type) },
                { default: () => 'Изменить' },
              ),
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'error',
                  onClick: () => confirmDelete(type),
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
  <div class="task-types">
    <n-data-table
      :columns="columns"
      :data="store.items"
      :loading="store.isLoading"
      :bordered="false"
      :row-key="(row: TaskTypeOut) => row.id"
    />

    <div v-if="canEdit">
      <n-button type="primary" @click="openCreate">
        <template #icon><n-icon :component="AddOutline" /></template>
        Добавить тип
      </n-button>
    </div>

    <n-modal
      v-model:show="isFormOpen"
      preset="card"
      :title="editingType ? 'Изменить тип задач' : 'Новый тип задач'"
      style="max-width: 440px"
    >
      <n-form
        ref="formRef"
        :model="{ name, abbreviation }"
        :rules="rules"
        label-placement="top"
        @submit.prevent="handleSave"
      >
        <n-form-item label="Название" path="name">
          <n-input v-model:value="name" />
        </n-form-item>
        <n-form-item label="Аббревиатура (префикс кодов задач)" path="abbreviation">
          <n-input
            :value="abbreviation"
            placeholder="Например, CLN"
            @update:value="abbreviation = $event.toUpperCase()"
          />
        </n-form-item>
        <p v-if="editingType" class="task-types__hint">
          Смена аббревиатуры не меняет коды уже созданных задач.
        </p>
        <n-form-item label="Цвет">
          <n-color-picker v-model:value="color" :modes="['hex']" :show-alpha="false" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="task-types__modal-actions">
          <n-button :disabled="isSaving" @click="isFormOpen = false">Отмена</n-button>
          <n-button type="primary" :loading="isSaving" @click="handleSave">Сохранить</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.task-types {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.task-types__hint {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.task-types__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

<style>
.task-types__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1, 4px);
}
</style>
