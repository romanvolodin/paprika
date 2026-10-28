<script setup lang="ts">
import { computed, h, watch } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import {
  NButton,
  NDataTable,
  NIcon,
  NPagination,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { CloudUploadOutline, ImageOutline } from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'
import { useVersionsStore } from '@/stores/versions'
import { formatFileSize, formatVideoTiming } from '@/utils/format'
import type { VersionOut } from '@/types/api'

const props = defineProps<{
  shotId: number
  canUpload: boolean
  canDelete: boolean
  // Lets the uploader delete their own versions only.
  canDeleteOwn: boolean
  uploadTo: RouteLocationRaw
}>()

const auth = useAuthStore()
const store = useVersionsStore()
const message = useMessage()
const dialog = useDialog()

watch(
  () => props.shotId,
  (shotId) => store.fetch(shotId),
  { immediate: true },
)

function confirmDelete(version: VersionOut) {
  dialog.warning({
    title: 'Удалить версию',
    content: `Удалить версию ${version.name}? Файлы будут удалены безвозвратно, имя освободится для новой загрузки.`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(props.shotId, version.id)
        message.success('Версия удалена.')
      } catch {
        message.error('Не удалось удалить версию.')
      }
    },
  })
}

function authorName(version: VersionOut): string {
  const author = version.created_by
  return author ? `${author.first_name} ${author.last_name}`.trim() : '—'
}

function canDeleteVersion(version: VersionOut): boolean {
  return props.canDelete || (props.canDeleteOwn && version.created_by?.id === auth.currentUser?.id)
}

const columns = computed<DataTableColumns<VersionOut>>(() => [
  {
    title: '',
    key: 'thumb',
    width: 120,
    render: (version) => {
      const href = version.converted ?? version.source
      return h(
        'a',
        { href, target: '_blank', rel: 'noopener', class: 'shot-versions__preview' },
        version.thumb
          ? h('img', { src: version.thumb, alt: version.name, loading: 'lazy' })
          : h(NIcon, { component: ImageOutline, size: 24 }),
      )
    },
  },
  {
    title: 'Версия',
    key: 'name',
    render: (version) => h('span', { class: 'mono' }, version.name),
  },
  {
    title: 'Тип',
    key: 'type',
    width: 100,
    render: (version) =>
      h(
        NTag,
        { size: 'small', round: true },
        { default: () => (version.type === 'video' ? 'Видео' : 'Изображение') },
      ),
  },
  {
    title: 'Разрешение',
    key: 'resolution',
    width: 120,
    render: (version) => `${version.width}×${version.height}`,
  },
  {
    title: 'Длительность',
    key: 'duration',
    width: 150,
    render: (version) => formatVideoTiming(version.duration, version.fps),
  },
  {
    title: 'Размер',
    key: 'file_size',
    width: 100,
    render: (version) => formatFileSize(version.file_size),
  },
  {
    title: 'Загрузил',
    key: 'created_by',
    render: (version) => authorName(version),
  },
  {
    title: 'Дата',
    key: 'created_at',
    width: 150,
    render: (version) =>
      new Date(version.created_at).toLocaleString('ru-RU', {
        dateStyle: 'short',
        timeStyle: 'short',
      }),
  },
  ...(props.canDelete || props.canDeleteOwn
    ? [
        {
          title: '',
          key: 'actions',
          width: 100,
          render: (version: VersionOut) =>
            canDeleteVersion(version)
              ? h(
                  NButton,
                  {
                    size: 'small',
                    quaternary: true,
                    type: 'error',
                    onClick: () => confirmDelete(version),
                  },
                  { default: () => 'Удалить' },
                )
              : null,
        },
      ]
    : []),
])
</script>

<template>
  <div class="shot-versions">
    <RouterLink v-if="canUpload" v-slot="{ href, navigate }" :to="uploadTo" custom>
      <n-button class="shot-versions__upload" type="primary" tag="a" :href="href" @click="navigate">
        <template #icon><n-icon :component="CloudUploadOutline" /></template>
        Загрузить версию
      </n-button>
    </RouterLink>

    <n-data-table
      :columns="columns"
      :data="store.items"
      :loading="store.isLoading"
      :bordered="false"
      :scroll-x="900"
      :row-key="(row: VersionOut) => row.id"
    />

    <div v-if="store.total > store.pageSize" class="shot-versions__pagination">
      <n-pagination
        :page="store.page"
        :page-size="store.pageSize"
        :item-count="store.total"
        @update:page="(page: number) => store.setPage(props.shotId, page)"
      />
    </div>
  </div>
</template>

<style scoped>
.shot-versions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-versions__upload {
  align-self: flex-start;
}

.shot-versions__pagination {
  display: flex;
  justify-content: flex-end;
}
</style>

<style>
.shot-versions__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 54px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--color-surface-muted, rgba(128, 128, 128, 0.12));
  color: var(--color-text-secondary);
}

.shot-versions__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
