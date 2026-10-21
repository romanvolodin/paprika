<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { NButton, NIcon, NProgress, useMessage } from 'naive-ui'
import { CloseOutline, CloudUploadOutline } from '@vicons/ionicons5'
import { useVersionsStore } from '@/stores/versions'
import { describeVersionUploadError } from '@/utils/apiError'
import { formatFileSize } from '@/utils/format'
import type { VersionOut } from '@/types/api'

const props = defineProps<{ shotId: number }>()
const emit = defineEmits<{ uploaded: [version: VersionOut] }>()

const ALLOWED_EXTENSIONS = ['mp4', 'jpg', 'jpeg', 'png']

const store = useVersionsStore()
const message = useMessage()

const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const previewUrl = ref('')

const isBusy = computed(() => store.uploadState !== 'idle')
// The extension decides, not the MIME type: some systems send none.
const isVideo = computed(() => file.value?.name.toLowerCase().endsWith('.mp4') ?? false)

function dropPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function choose(candidate: File) {
  const extension = candidate.name.split('.').pop()?.toLowerCase() ?? ''
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    message.error('Поддерживаются файлы mp4 (h264), jpg и png.')
    return
  }
  dropPreview()
  file.value = candidate
  previewUrl.value = URL.createObjectURL(candidate)
}

function reset() {
  dropPreview()
  file.value = null
}

function pickFile() {
  fileInput.value?.click()
}

function handleFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const chosen = input.files?.[0]
  // Reset so choosing the same file again (after a reset) still fires.
  input.value = ''
  if (chosen) choose(chosen)
}

function handleDrop(event: DragEvent) {
  const dropped = Array.from(event.dataTransfer?.files ?? [])
  if (dropped.length === 0) return
  if (dropped.length > 1) message.info('Версия загружается по одному файлу, взят первый.')
  choose(dropped[0])
}

async function submit() {
  if (!file.value) return
  try {
    const version = await store.upload(props.shotId, file.value)
    emit('uploaded', version)
  } catch (error) {
    message.error(describeVersionUploadError(error))
  }
}

onBeforeUnmount(dropPreview)
</script>

<template>
  <div class="version-upload">
    <div class="version-upload__main">
      <div
        v-if="!file"
        class="version-upload__drop"
        data-test="drop-zone"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <n-button type="primary" @click="pickFile">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          Выбрать файл
        </n-button>
        <p>или перетащите файл сюда</p>
        <p class="version-upload__hint">Поддерживаются mp4 (h264), jpg и png.</p>
      </div>

      <div v-else class="version-upload__preview" data-test="preview">
        <div class="version-upload__file-header">
          <span class="version-upload__file-name mono">{{ file.name }}</span>
          <n-button quaternary circle :disabled="isBusy" aria-label="Сбросить файл" @click="reset">
            <template #icon><n-icon :component="CloseOutline" /></template>
          </n-button>
        </div>
        <div class="version-upload__media">
          <video v-if="isVideo" :src="previewUrl" controls preload="metadata" />
          <img v-else :src="previewUrl" :alt="file.name" />
        </div>
      </div>

      <input
        ref="fileInput"
        class="version-upload__file-input"
        type="file"
        accept=".mp4,.jpg,.jpeg,.png,video/mp4,image/jpeg,image/png"
        @change="handleFileChosen"
      />
    </div>

    <aside class="version-upload__side">
      <h2 class="version-upload__heading">Загрузить версию</h2>

      <dl v-if="file" class="version-upload__facts">
        <dt>Файл</dt>
        <dd class="mono">{{ file.name }}</dd>
        <dt>Размер</dt>
        <dd>{{ formatFileSize(file.size) }}</dd>
      </dl>

      <div class="version-upload__submit">
        <n-progress
          v-if="store.uploadState === 'uploading'"
          type="line"
          :percentage="store.uploadProgress"
          :height="12"
        />
        <span v-else-if="store.uploadState === 'processing'" class="version-upload__processing">
          Файл отправлен, идёт обработка…
        </span>
        <n-button type="primary" :disabled="!file || isBusy" @click="submit">
          Отправить версию
        </n-button>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.version-upload {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: var(--space-4);
  min-height: 0;
}

.version-upload__main,
.version-upload__preview {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.version-upload__drop {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.version-upload__drop p {
  margin: 0;
}

.version-upload__hint {
  font-size: var(--text-sm, 13px);
}

.version-upload__preview {
  flex: 1;
  gap: var(--space-2);
}

.version-upload__file-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.version-upload__file-name {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.version-upload__media {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: #000;
}

.version-upload__media video,
.version-upload__media img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.version-upload__file-input {
  display: none;
}

.version-upload__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.version-upload__heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.version-upload__facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  font-size: var(--text-sm, 13px);
}

.version-upload__facts dt {
  color: var(--color-text-secondary);
}

.version-upload__facts dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.version-upload__submit {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: auto;
}

.version-upload__processing {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

/* On a narrow screen the columns stack and the page scrolls. */
@media (max-width: 900px) {
  .version-upload {
    flex: none;
    grid-template-columns: minmax(0, 1fr);
  }

  .version-upload__preview,
  .version-upload__drop {
    flex: none;
    min-height: 240px;
  }

  .version-upload__media {
    aspect-ratio: 16 / 9;
  }
}
</style>
