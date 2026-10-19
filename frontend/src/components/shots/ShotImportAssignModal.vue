<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NInput, NModal, NSelect } from 'naive-ui'
import * as tasksApi from '@/api/tasks'
import { useRemoteSearchOptions } from '@/composables/useRemoteSearchOptions'
import type { ImportTask, NewImportTask } from '@/utils/shotImport'
import type { ShotGroupOut, TaskOut, TaskTypeOut } from '@/types/api'

const props = defineProps<{
  show: boolean
  mode: 'group' | 'task'
  rowCount: number
  projectId: number
  groups: ShotGroupOut[]
  taskTypes: TaskTypeOut[]
  /** Groups given to rows in this import that the project doesn't have yet. */
  pendingGroups: string[]
  /** New tasks given to rows in this import that don't exist yet. */
  pendingTasks: NewImportTask[]
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'add-group': [name: string]
  'add-task': [task: ImportTask]
}>()

// --- Group: an existing one or a name typed in (created on import) --------

const groupName = ref<string | null>(null)
const groupOptions = computed(() => [
  ...props.groups.map((group) => ({ label: group.name, value: group.name })),
  ...props.pendingGroups.map((name) => ({ label: `${name} (новая)`, value: name })),
])

// --- Task: pick an existing one, or switch to making a new one ------------

const taskMode = ref<'pick' | 'create'>('pick')
// A number is an existing task's id; a string is the key of a pending new task.
const pickedTaskId = ref<number | string | null>(null)
const lastQuery = ref('')
const newName = ref('')
const newTypeId = ref<number | null>(null)
const foundTasks = new Map<number, TaskOut>()

function pendingKey(task: NewImportTask): string {
  return `new:${task.typeId}:${task.name}`
}

const {
  options: remoteTaskOptions,
  loading: isSearching,
  search,
  loadInitial,
} = useRemoteSearchOptions(
  (query) =>
    tasksApi
      .listTasks(props.projectId, { search: query || undefined, page_size: 20 })
      .then((result) => {
        for (const task of result.items) foundTasks.set(task.id, task)
        return result.items
      }),
  (task) => ({ label: `${task.code} · ${task.name}`, value: task.id }),
)

// The new tasks already given to other rows come first, so they can be
// found again; the project's own tasks come from the search.
const taskOptions = computed(() => {
  const query = lastQuery.value.trim().toLowerCase()
  const pending = props.pendingTasks
    .filter((task) => task.name.toLowerCase().includes(query))
    .map((task) => ({
      label: `+ ${task.name} (${task.typeName}) · новая`,
      value: pendingKey(task),
    }))
  return [...pending, ...remoteTaskOptions.value]
})

const typeOptions = computed(() =>
  props.taskTypes.map((type) => ({ label: `${type.name} (${type.abbreviation})`, value: type.id })),
)

function handleSearch(query: string) {
  lastQuery.value = query
  search(query)
}

function startCreating() {
  newName.value = lastQuery.value.trim()
  taskMode.value = 'create'
}

watch(
  () => props.show,
  (isShown) => {
    if (!isShown) return
    groupName.value = null
    taskMode.value = 'pick'
    pickedTaskId.value = null
    lastQuery.value = ''
    newName.value = ''
    newTypeId.value = null
  },
)

const canConfirm = computed(() => {
  if (props.mode === 'group') return Boolean(groupName.value?.trim())
  if (taskMode.value === 'pick') return pickedTaskId.value !== null
  return newName.value.trim() !== '' && newTypeId.value !== null
})

const title = computed(() =>
  props.mode === 'group' ? 'Группа для выделенных строк' : 'Задача для выделенных строк',
)

function confirm() {
  if (!canConfirm.value) return
  if (props.mode === 'group') {
    emit('add-group', groupName.value!.trim())
  } else if (taskMode.value === 'pick') {
    const picked = pickedTaskId.value!
    const pending = props.pendingTasks.find((task) => pendingKey(task) === picked)
    if (pending) {
      emit('add-task', { ...pending })
    } else {
      const task = typeof picked === 'number' ? foundTasks.get(picked) : undefined
      if (!task) return
      emit('add-task', { kind: 'existing', taskId: task.id, name: task.name, code: task.code })
    }
  } else {
    const type = props.taskTypes.find((candidate) => candidate.id === newTypeId.value)
    if (!type) return
    emit('add-task', {
      kind: 'new',
      name: newName.value.trim(),
      typeId: type.id,
      typeName: type.name,
    })
  }
  emit('update:show', false)
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="title"
    style="max-width: 460px"
    @update:show="(value: boolean) => emit('update:show', value)"
  >
    <p class="assign__hint">Выбрано строк: {{ rowCount }}</p>

    <template v-if="mode === 'group'">
      <n-select
        v-model:value="groupName"
        filterable
        tag
        clearable
        placeholder="Выберите группу или введите новое название"
        :options="groupOptions"
      />
      <p class="assign__hint">Если такой группы в проекте нет, она будет создана при импорте.</p>
    </template>

    <template v-else-if="taskMode === 'pick'">
      <n-select
        v-model:value="pickedTaskId"
        filterable
        remote
        clearable
        placeholder="Начните вводить название задачи"
        :options="taskOptions"
        :loading="isSearching"
        @search="handleSearch"
        @focus="loadInitial"
      >
        <template #empty>
          <span class="assign__hint">Подходящих задач нет.</span>
        </template>
      </n-select>
      <n-button text type="primary" class="assign__switch" @click="startCreating">
        Создать новую задачу{{ lastQuery.trim() ? ` «${lastQuery.trim()}»` : '' }}
      </n-button>
    </template>

    <template v-else>
      <div class="assign__fields">
        <n-input v-model:value="newName" placeholder="Название задачи" maxlength="255" />
        <n-select v-model:value="newTypeId" placeholder="Тип задачи" :options="typeOptions" />
      </div>
      <n-button text type="primary" class="assign__switch" @click="taskMode = 'pick'">
        Выбрать существующую
      </n-button>
    </template>

    <template #footer>
      <div class="assign__footer">
        <n-button @click="emit('update:show', false)">Отмена</n-button>
        <n-button type="primary" :disabled="!canConfirm" @click="confirm">Добавить</n-button>
      </div>
    </template>
  </n-modal>
</template>

<style scoped>
.assign__hint {
  margin: var(--space-2) 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.assign__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.assign__switch {
  margin-top: var(--space-3);
}

.assign__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
