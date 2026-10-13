<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import {
  NButton,
  NDataTable,
  NIcon,
  NInput,
  NModal,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useShotGroupsStore } from '@/stores/shotGroups'
import { firstValidationMessage } from '@/utils/apiError'
import type { ShotGroupOut } from '@/types/api'

const props = defineProps<{ projectId: number; canWrite: boolean }>()

const store = useShotGroupsStore()
const message = useMessage()
const dialog = useDialog()

const newName = ref('')
const isAdding = ref(false)

const renamingGroup = ref<ShotGroupOut | null>(null)
const renameValue = ref('')
const isRenaming = ref(false)

watch(
  () => props.projectId,
  (projectId) => store.fetch(projectId),
  { immediate: true },
)

function describeError(error: unknown, fallback: string): string {
  return firstValidationMessage(error)?.includes('already exists')
    ? 'Группа с таким названием уже есть в проекте.'
    : fallback
}

async function handleAdd() {
  const name = newName.value.trim()
  if (!name) return
  isAdding.value = true
  try {
    await store.create(props.projectId, name)
    newName.value = ''
  } catch (error) {
    message.error(describeError(error, 'Не удалось создать группу.'))
  } finally {
    isAdding.value = false
  }
}

function startRename(group: ShotGroupOut) {
  renamingGroup.value = group
  renameValue.value = group.name
}

async function handleRename() {
  const group = renamingGroup.value
  const name = renameValue.value.trim()
  if (!group || !name) return
  isRenaming.value = true
  try {
    await store.rename(props.projectId, group.id, name)
    renamingGroup.value = null
  } catch (error) {
    message.error(describeError(error, 'Не удалось переименовать группу.'))
  } finally {
    isRenaming.value = false
  }
}

function confirmDelete(group: ShotGroupOut) {
  dialog.warning({
    title: 'Удалить группу',
    content: `Удалить группу «${group.name}»? Кадры останутся, но выйдут из этой группы.`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(props.projectId, group.id)
        message.success('Группа удалена.')
      } catch {
        message.error('Не удалось удалить группу.')
      }
    },
  })
}

const columns = computed<DataTableColumns<ShotGroupOut>>(() => [
  { title: 'Название', key: 'name' },
  ...(props.canWrite
    ? [
        {
          title: '',
          key: 'actions',
          width: 220,
          render: (group: ShotGroupOut) =>
            h('div', { class: 'shot-groups__actions' }, [
              h(
                NButton,
                { size: 'small', quaternary: true, onClick: () => startRename(group) },
                { default: () => 'Переименовать' },
              ),
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'error',
                  onClick: () => confirmDelete(group),
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
  <div class="shot-groups">
    <n-data-table
      :columns="columns"
      :data="store.items"
      :loading="store.isLoading"
      :bordered="false"
      :row-key="(row: ShotGroupOut) => row.id"
    />

    <div v-if="canWrite" class="shot-groups__add">
      <n-input
        v-model:value="newName"
        placeholder="Название новой группы"
        style="max-width: 320px"
        @keydown.enter.prevent="handleAdd"
      />
      <n-button type="primary" :disabled="!newName.trim()" :loading="isAdding" @click="handleAdd">
        <template #icon><n-icon :component="AddOutline" /></template>
        Добавить
      </n-button>
    </div>

    <n-modal
      :show="renamingGroup !== null"
      preset="card"
      title="Переименовать группу"
      style="max-width: 400px"
      @update:show="renamingGroup = null"
    >
      <n-input v-model:value="renameValue" @keydown.enter.prevent="handleRename" />
      <template #footer>
        <div class="shot-groups__modal-actions">
          <n-button @click="renamingGroup = null">Отмена</n-button>
          <n-button
            type="primary"
            :disabled="!renameValue.trim()"
            :loading="isRenaming"
            @click="handleRename"
          >
            Сохранить
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.shot-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-groups__add {
  display: flex;
  gap: var(--space-2);
}

.shot-groups__modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

<style>
.shot-groups__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1, 4px);
}
</style>
