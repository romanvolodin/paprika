<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import {
  NDataTable,
  NIcon,
  NInput,
  NPagination,
  NSelect,
  NTag,
  type DataTableColumns,
} from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { useProjectPageStore } from '@/stores/projectPage'
import { useProjectTasksStore } from '@/stores/projectTasks'
import type { TaskOut } from '@/types/api'

const page = useProjectPageStore()
const tasks = useProjectTasksStore()

const searchInput = ref('')

watch(
  () => page.project?.id,
  (projectId) => {
    if (projectId === undefined || !page.project) return
    searchInput.value = ''
    tasks.open(projectId, page.project.company_id)
  },
  { immediate: true },
)

const debouncedSearch = useDebounceFn((value: string) => {
  tasks.setSearch(value)
}, 300)

function handleSearchInput(value: string) {
  searchInput.value = value
  debouncedSearch(value)
}

const typeById = computed(() => new Map(tasks.types.map((type) => [type.id, type])))

const typeOptions = computed(() =>
  tasks.types.map((type) => ({ value: type.id, label: type.name })),
)

const columns = computed<DataTableColumns<TaskOut>>(() => [
  {
    title: 'Код',
    key: 'code',
    width: 120,
    render: (task) => h('span', { class: 'mono' }, task.code),
  },
  {
    title: 'Название',
    key: 'name',
  },
  {
    title: 'Тип',
    key: 'type_id',
    width: 180,
    render: (task) => {
      const type = typeById.value.get(task.type_id)
      if (!type) return null
      return h(
        NTag,
        {
          size: 'small',
          round: true,
          color: {
            color: `${type.color}26`,
            borderColor: type.color,
            textColor: type.color,
          },
        },
        { default: () => type.name },
      )
    },
  },
  {
    title: 'Кадров',
    key: 'shot_ids',
    width: 100,
    render: (task) => task.shot_ids.length,
  },
])
</script>

<template>
  <section class="project-tasks">
    <div class="project-tasks__filters">
      <n-input
        :value="searchInput"
        placeholder="Поиск по названию или коду"
        clearable
        style="max-width: 320px"
        @update:value="handleSearchInput"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        :value="tasks.typeId"
        :options="typeOptions"
        clearable
        placeholder="Все типы"
        style="max-width: 200px"
        @update:value="tasks.setType"
      />
    </div>

    <n-data-table
      :columns="columns"
      :data="tasks.items"
      :loading="tasks.isLoading"
      :bordered="false"
      :row-key="(row: TaskOut) => row.id"
    />

    <div class="project-tasks__pagination">
      <n-pagination
        :page="tasks.page"
        :page-size="tasks.pageSize"
        :item-count="tasks.total"
        @update:page="tasks.setPage"
      />
    </div>
  </section>
</template>

<style scoped>
.project-tasks {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 960px;
}

.project-tasks__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.project-tasks__pagination {
  display: flex;
  justify-content: flex-end;
}
</style>
