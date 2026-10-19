<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCheckbox,
  NDataTable,
  NInput,
  NInputNumber,
  NSelect,
  NTag,
  type DataTableColumns,
} from 'naive-ui'
import ShotImportAssignModal from '@/components/shots/ShotImportAssignModal.vue'
import { useShotImportStore } from '@/stores/shotImport'
import {
  IMPORT_FIELDS,
  rowsInRange,
  rowsWithSameTaskText,
  type ImportField,
  type ImportRow,
  type ImportTask,
} from '@/utils/shotImport'

const emit = defineEmits<{ submit: []; 'change-file': [] }>()

const store = useShotImportStore()

const checkedKeys = ref<number[]>([])
const assignMode = ref<'group' | 'task' | null>(null)

watch(
  () => store.rows,
  () => {
    checkedKeys.value = []
  },
)

const fieldOptions = IMPORT_FIELDS.map((field) => ({ label: field.label, value: field.value }))
const sheetOptions = computed(() =>
  store.sheets.map((sheet, index) => ({ label: sheet.name, value: index })),
)

const hasTaskTextColumn = computed(() => store.mapping.includes('taskText'))
const canSelectSameText = computed(() => checkedKeys.value.length === 1 && hasTaskTextColumn.value)

function selectAll() {
  checkedKeys.value = store.rows.map((row) => row.id)
}

function selectSameText() {
  const [rowId] = checkedKeys.value
  if (rowId === undefined) return
  const ids = rowsWithSameTaskText(store.rows, store.mapping, rowId)
  if (ids.length > 0) checkedKeys.value = ids
}

const rangeFrom = ref<number | null>(null)
const rangeTo = ref<number | null>(null)

function selectRange() {
  if (rangeFrom.value === null || rangeTo.value === null) return
  checkedKeys.value = rowsInRange(store.rows, rangeFrom.value, rangeTo.value)
}

function selectProblemRows() {
  checkedKeys.value = [...store.problems.keys()]
}

function skipChecked(skipped: boolean) {
  store.setSkipped(checkedKeys.value, skipped)
}

function handleAddGroup(name: string) {
  store.addGroup(checkedKeys.value, name)
}

function handleAddTask(task: ImportTask) {
  store.addTask(checkedKeys.value, task)
}

function describeTask(task: ImportTask): string {
  return task.kind === 'existing'
    ? `${task.code} ${task.name}`
    : `+ ${task.name} (${task.typeName})`
}

const COLUMN_WIDTH = 200
const FIXED_WIDTH = 50 + 70 + 240 + 90 + 280

const columns = computed<DataTableColumns<ImportRow>>(() => {
  const dataColumns = Array.from({ length: store.columnCount }, (_, column) => ({
    key: `column-${column}`,
    width: COLUMN_WIDTH,
    // No `ellipsis` here: naive-ui would wrap the header select and the name
    // input in a shrink-to-fit box, and their 100% width would collapse to 0.
    title: () =>
      h(NSelect, {
        value: store.mapping[column] ?? null,
        options: fieldOptions,
        placeholder: 'Не использовать',
        clearable: true,
        size: 'small',
        'onUpdate:value': (field: ImportField | null) => store.setField(column, field),
      }),
    render: (row: ImportRow) =>
      store.mapping[column] === 'name'
        ? h(NInput, {
            value: row.cells[column],
            size: 'small',
            disabled: row.skipped,
            'onUpdate:value': (value: string) => store.setCell(row.id, column, value),
          })
        : h('div', { class: 'import-cell', title: row.cells[column] }, row.cells[column] ?? ''),
  }))

  return [
    { type: 'selection', fixed: 'left', width: 50 },
    { key: 'sheetRow', title: '№', width: 70, render: (row) => row.sheetRow },
    ...dataColumns,
    {
      key: 'assigned',
      title: 'Группы и задачи',
      width: 240,
      render: (row) =>
        h('div', { class: 'import-chips' }, [
          ...row.groups.map((name) =>
            h(
              NTag,
              {
                size: 'small',
                round: true,
                closable: true,
                onClose: () => store.removeGroup(row.id, name),
              },
              { default: () => name },
            ),
          ),
          ...row.tasks.map((task, index) =>
            h(
              NTag,
              {
                size: 'small',
                type: task.kind === 'new' ? 'success' : 'default',
                closable: true,
                onClose: () => store.removeTask(row.id, index),
              },
              { default: () => describeTask(task) },
            ),
          ),
        ]),
    },
    {
      key: 'skipped',
      title: 'Пропустить',
      width: 90,
      render: (row) =>
        h(NCheckbox, {
          checked: row.skipped,
          'onUpdate:checked': (value: boolean) => store.setSkipped([row.id], value),
        }),
    },
    {
      key: 'problems',
      title: 'Проблемы',
      width: 280,
      render: (row) =>
        h(
          'div',
          { class: 'import-problems' },
          (store.problems.get(row.id) ?? []).map((text) => h('div', text)),
        ),
    },
  ]
})

const tableWidth = computed(() => FIXED_WIDTH + store.columnCount * COLUMN_WIDTH)

function rowClassName(row: ImportRow): string {
  if (row.skipped) return 'import-row--skipped'
  return store.problems.has(row.id) ? 'import-row--problem' : ''
}

const summary = computed(() => {
  const parts = [`Будет создано кадров: ${store.shotCount}`]
  if (store.skippedCount > 0) parts.push(`пропущено: ${store.skippedCount}`)
  if (store.problems.size > 0) parts.push(`строк с проблемами: ${store.problems.size}`)
  return parts.join(' · ')
})

const hint = computed(() => {
  if (!store.hasNameColumn) return 'Выберите над одним из столбцов поле «Имя кадра».'
  if (store.hasTimecodeColumn && !store.isFpsValid) return 'Укажите частоту кадров (целое число).'
  return ''
})
</script>

<template>
  <div class="import-preview">
    <div class="import-preview__bar">
      <span class="import-preview__file">{{ store.fileName }}</span>
      <n-button size="small" @click="emit('change-file')">Выбрать другой файл</n-button>
      <n-select
        v-if="store.sheets.length > 1"
        :value="store.sheetIndex"
        :options="sheetOptions"
        size="small"
        style="width: 200px"
        @update:value="store.selectSheet"
      />
      <label class="import-preview__fps">
        Частота кадров
        <n-input-number
          v-model:value="store.fps"
          size="small"
          :min="1"
          :max="240"
          :precision="0"
          :show-button="false"
          style="width: 80px"
        />
      </label>
    </div>

    <div class="import-preview__bar">
      <span class="import-preview__selected">Выделено: {{ checkedKeys.length }}</span>
      <n-button size="small" @click="selectAll">Выделить все</n-button>
      <n-button size="small" :disabled="checkedKeys.length === 0" @click="checkedKeys = []">
        Снять выделение
      </n-button>
      <n-button size="small" :disabled="store.problems.size === 0" @click="selectProblemRows">
        Выделить строки с проблемами
      </n-button>
      <n-button size="small" :disabled="!canSelectSameText" @click="selectSameText">
        Выделить с таким же текстом задачи
      </n-button>
      <span class="import-preview__range">
        Строки с
        <n-input-number
          v-model:value="rangeFrom"
          size="small"
          :min="1"
          :precision="0"
          :show-button="false"
          style="width: 70px"
        />
        по
        <n-input-number
          v-model:value="rangeTo"
          size="small"
          :min="1"
          :precision="0"
          :show-button="false"
          style="width: 70px"
        />
        <n-button
          size="small"
          :disabled="rangeFrom === null || rangeTo === null"
          @click="selectRange"
        >
          Выделить
        </n-button>
      </span>
      <n-button size="small" :disabled="checkedKeys.length === 0" @click="skipChecked(true)">
        Пропустить
      </n-button>
      <n-button size="small" :disabled="checkedKeys.length === 0" @click="skipChecked(false)">
        Не пропускать
      </n-button>
      <n-button size="small" :disabled="checkedKeys.length === 0" @click="assignMode = 'group'">
        Группа…
      </n-button>
      <n-button size="small" :disabled="checkedKeys.length === 0" @click="assignMode = 'task'">
        Задача…
      </n-button>
    </div>

    <n-alert v-for="text in store.generalProblems" :key="text" type="error">{{ text }}</n-alert>

    <n-data-table
      v-model:checked-row-keys="checkedKeys"
      :columns="columns"
      :data="store.rows"
      :row-key="(row: ImportRow) => row.id"
      :row-class-name="rowClassName"
      :pagination="{ pageSize: 50 }"
      :scroll-x="tableWidth"
      :max-height="560"
      :bordered="false"
      size="small"
    />

    <div class="import-preview__footer">
      <span class="import-preview__summary">{{ summary }}</span>
      <span v-if="hint" class="import-preview__hint">{{ hint }}</span>
      <n-button
        type="primary"
        :disabled="!store.canSubmit"
        :loading="store.isSubmitting"
        @click="emit('submit')"
      >
        Создать кадры
      </n-button>
    </div>

    <shot-import-assign-modal
      v-if="store.project"
      :show="assignMode !== null"
      :mode="assignMode ?? 'group'"
      :row-count="checkedKeys.length"
      :project-id="store.project.id"
      :groups="store.groups"
      :task-types="store.taskTypes"
      :pending-groups="store.pendingGroups"
      :pending-tasks="store.pendingTasks"
      @update:show="(value: boolean) => !value && (assignMode = null)"
      @add-group="handleAddGroup"
      @add-task="handleAddTask"
    />
  </div>
</template>

<style scoped>
.import-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.import-preview__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.import-preview__file {
  font-weight: 600;
}

.import-preview__fps {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.import-preview__range {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.import-preview__selected {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.import-preview__footer {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.import-preview__summary {
  color: var(--color-text-secondary);
}

.import-preview__hint {
  color: var(--color-status-progress);
  font-size: var(--text-sm, 13px);
}

.import-preview__footer :deep(.n-button) {
  margin-left: auto;
}

:deep(.import-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.import-chips) {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}

:deep(.import-problems) {
  color: var(--color-status-blocked);
  font-size: var(--text-sm, 13px);
}

:deep(.import-row--skipped td) {
  opacity: 0.45;
}

:deep(.import-row--problem td) {
  background: color-mix(in srgb, var(--color-status-blocked) 8%, transparent);
}
</style>
