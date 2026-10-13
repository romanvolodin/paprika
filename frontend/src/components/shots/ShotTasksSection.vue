<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import {
  NButton,
  NIcon,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NTabPane,
  NTabs,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import * as tasksApi from '@/api/tasks'
import { useRemoteSearchOptions } from '@/composables/useRemoteSearchOptions'
import { TaskNotPlacedError, useShotTasksStore } from '@/stores/shotTasks'
import { describeShotTaskError } from '@/utils/apiError'
import { tagColor } from '@/utils/color'
import { formatHours } from '@/utils/format'
import type { ProjectMemberOut, ShotTaskOut, TaskOut } from '@/types/api'

const props = defineProps<{
  shotId: number
  projectId: number
  companyId: number
  members: ProjectMemberOut[]
  canWrite: boolean
}>()

const store = useShotTasksStore()
const message = useMessage()
const dialog = useDialog()

watch(
  () => [props.shotId, props.projectId, props.companyId] as const,
  ([shotId, projectId, companyId]) => store.open({ shotId, projectId, companyId }),
  { immediate: true },
)

const typeById = computed(() => new Map(store.types.map((type) => [type.id, type])))
const statusById = computed(() => new Map(store.statuses.map((status) => [status.id, status])))

// Statuses of the main workflow first (by order), side statuses after.
const statusOptions = computed(() =>
  [...store.statuses]
    .sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity))
    .map((status) => ({ label: status.name, value: status.id })),
)
const typeOptions = computed(() =>
  store.types.map((type) => ({ label: `${type.name} (${type.abbreviation})`, value: type.id })),
)
const assigneeOptions = computed(() =>
  props.members.map((member) => ({
    label: `${member.first_name} ${member.last_name}`.trim(),
    value: member.user_id,
  })),
)

async function change(shotTask: ShotTaskOut, input: Parameters<typeof store.update>[1]) {
  try {
    await store.update(shotTask.id, input)
  } catch (error) {
    message.error(describeShotTaskError(error, 'Не удалось сохранить изменение.'))
  }
}

// --- Hours -------------------------------------------------------------

const hoursTask = ref<ShotTaskOut | null>(null)
const estimatedHours = ref<number | null>(null)
const actualHours = ref<number | null>(null)
const isSavingHours = ref(false)

function startEditHours(shotTask: ShotTaskOut) {
  hoursTask.value = shotTask
  estimatedHours.value = shotTask.estimated_hours
  actualHours.value = shotTask.actual_hours
}

async function saveHours() {
  const shotTask = hoursTask.value
  if (!shotTask) return
  isSavingHours.value = true
  try {
    await store.update(shotTask.id, {
      estimated_hours: estimatedHours.value,
      actual_hours: actualHours.value,
    })
    hoursTask.value = null
  } catch (error) {
    message.error(describeShotTaskError(error, 'Не удалось сохранить часы.'))
  } finally {
    isSavingHours.value = false
  }
}

// --- Taking a task off the shot ---------------------------------------

function confirmRemove(shotTask: ShotTaskOut) {
  dialog.warning({
    title: 'Снять задачу с кадра',
    content: `Снять задачу ${shotTask.task.code} с кадра? Статус, исполнитель и часы на этом кадре будут удалены, сама задача останется в проекте.`,
    positiveText: 'Снять',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(shotTask.id)
        message.success('Задача снята с кадра.')
      } catch {
        message.error('Не удалось снять задачу с кадра.')
      }
    },
  })
}

// --- Adding a task ------------------------------------------------------

type AddMode = 'existing' | 'new'

const isAddOpen = ref(false)
const addMode = ref<AddMode>('existing')
const isAdding = ref(false)
const selectedTaskId = ref<number | null>(null)
const newName = ref('')
const newTypeId = ref<number | null>(null)

const {
  options: taskOptions,
  loading: isSearchingTasks,
  search: searchTasks,
  loadInitial: loadInitialTasks,
} = useRemoteSearchOptions(
  (query: string) =>
    tasksApi
      .listTasks(props.projectId, { search: query || undefined, page_size: 20 })
      // A task can be on a shot only once, so hide the ones already here.
      .then((result) => result.items.filter((task) => !task.shot_ids.includes(props.shotId))),
  (task: TaskOut) => ({ value: task.id, label: `${task.code} ${task.name}` }),
)

function openAdd() {
  addMode.value = 'existing'
  selectedTaskId.value = null
  newName.value = ''
  newTypeId.value = null
  taskOptions.value = []
  isAddOpen.value = true
}

const canSubmitAdd = computed(() =>
  addMode.value === 'existing'
    ? selectedTaskId.value !== null
    : newName.value.trim() !== '' && newTypeId.value !== null,
)

async function handleAdd() {
  if (!canSubmitAdd.value) return
  isAdding.value = true
  try {
    if (addMode.value === 'existing') {
      await store.addExisting(selectedTaskId.value as number)
    } else {
      await store.createAndAdd({ name: newName.value.trim(), type_id: newTypeId.value as number })
    }
    isAddOpen.value = false
  } catch (error) {
    if (error instanceof TaskNotPlacedError) {
      message.warning(
        'Задача создана, но не поставлена на кадр. Найдите её в списке существующих задач.',
      )
      isAddOpen.value = false
    } else {
      message.error(describeShotTaskError(error, 'Не удалось добавить задачу.'))
    }
  } finally {
    isAdding.value = false
  }
}

// --- Table ---------------------------------------------------------------

const columns = computed<DataTableColumns<ShotTaskOut>>(() => [
  {
    title: 'Задача',
    key: 'task',
    render: (shotTask) =>
      h('div', { class: 'shot-tasks__task' }, [
        h('span', { class: 'mono' }, shotTask.task.code),
        h('span', null, shotTask.task.name),
      ]),
  },
  {
    title: 'Тип',
    key: 'type',
    width: 130,
    render: (shotTask) => {
      const type = typeById.value.get(shotTask.task.type_id)
      return type
        ? h(
            NTag,
            { size: 'small', round: true, color: tagColor(type.color) },
            { default: () => type.name },
          )
        : null
    },
  },
  {
    title: 'Статус',
    key: 'status',
    width: 170,
    render: (shotTask) => {
      if (props.canWrite) {
        return h(NSelect, {
          size: 'small',
          value: shotTask.status_id,
          options: statusOptions.value,
          onUpdateValue: (value: number) => change(shotTask, { status_id: value }),
        })
      }
      const status = statusById.value.get(shotTask.status_id)
      return status
        ? h(
            NTag,
            { size: 'small', round: true, color: tagColor(status.color) },
            { default: () => status.name },
          )
        : null
    },
  },
  {
    title: 'Исполнитель',
    key: 'assignee',
    width: 200,
    render: (shotTask) => {
      if (props.canWrite) {
        return h(NSelect, {
          size: 'small',
          clearable: true,
          placeholder: 'Не назначен',
          value: shotTask.assignee?.id ?? null,
          options: assigneeOptions.value,
          onUpdateValue: (value: number | null) => change(shotTask, { assignee_id: value }),
        })
      }
      const assignee = shotTask.assignee
      return assignee ? `${assignee.first_name} ${assignee.last_name}`.trim() : '—'
    },
  },
  {
    title: 'Часы (план / факт)',
    key: 'hours',
    width: 150,
    render: (shotTask) => formatHours(shotTask.estimated_hours, shotTask.actual_hours),
  },
  ...(props.canWrite
    ? [
        {
          title: '',
          key: 'actions',
          width: 190,
          render: (shotTask: ShotTaskOut) =>
            h('div', { class: 'shot-tasks__actions' }, [
              h(
                NButton,
                { size: 'small', quaternary: true, onClick: () => startEditHours(shotTask) },
                { default: () => 'Часы' },
              ),
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'error',
                  onClick: () => confirmRemove(shotTask),
                },
                { default: () => 'Снять' },
              ),
            ]),
        },
      ]
    : []),
])
</script>

<template>
  <div class="shot-tasks">
    <n-data-table
      :columns="columns"
      :data="store.items"
      :loading="store.isLoading"
      :bordered="false"
      :scroll-x="880"
      :row-key="(row: ShotTaskOut) => row.id"
    />

    <div v-if="canWrite">
      <n-button type="primary" @click="openAdd">
        <template #icon><n-icon :component="AddOutline" /></template>
        Добавить задачу
      </n-button>
    </div>

    <n-modal
      v-model:show="isAddOpen"
      preset="card"
      title="Добавить задачу на кадр"
      style="max-width: 480px"
      :mask-closable="!isAdding"
    >
      <n-tabs v-model:value="addMode" type="segment" animated>
        <n-tab-pane name="existing" tab="Существующая">
          <n-form label-placement="top" @submit.prevent="handleAdd">
            <n-form-item label="Задача проекта">
              <n-select
                v-model:value="selectedTaskId"
                filterable
                remote
                clearable
                placeholder="Код или название"
                :options="taskOptions"
                :loading="isSearchingTasks"
                @search="searchTasks"
                @focus="loadInitialTasks"
              />
            </n-form-item>
          </n-form>
        </n-tab-pane>
        <n-tab-pane name="new" tab="Новая">
          <n-form label-placement="top" @submit.prevent="handleAdd">
            <n-form-item label="Название">
              <n-input v-model:value="newName" placeholder="Например, Замена неба" />
            </n-form-item>
            <n-form-item label="Тип">
              <n-select v-model:value="newTypeId" :options="typeOptions" />
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>
      <template #footer>
        <div class="shot-tasks__modal-actions">
          <n-button :disabled="isAdding" @click="isAddOpen = false">Отмена</n-button>
          <n-button type="primary" :disabled="!canSubmitAdd" :loading="isAdding" @click="handleAdd">
            Добавить
          </n-button>
        </div>
      </template>
    </n-modal>

    <n-modal
      :show="hoursTask !== null"
      preset="card"
      title="Часы"
      style="max-width: 360px"
      @update:show="hoursTask = null"
    >
      <n-form label-placement="top">
        <n-form-item label="Плановые часы">
          <n-input-number v-model:value="estimatedHours" :min="0" :precision="2" clearable />
        </n-form-item>
        <n-form-item label="Фактические часы">
          <n-input-number v-model:value="actualHours" :min="0" :precision="2" clearable />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="shot-tasks__modal-actions">
          <n-button :disabled="isSavingHours" @click="hoursTask = null">Отмена</n-button>
          <n-button type="primary" :loading="isSavingHours" @click="saveHours">Сохранить</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.shot-tasks {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-tasks__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

<style>
.shot-tasks__task {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shot-tasks__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1, 4px);
}
</style>
