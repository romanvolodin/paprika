<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NProgress, useMessage } from 'naive-ui'
import { CloudUploadOutline } from '@vicons/ionicons5'
import { useVersionsStore } from '@/stores/versions'
import { describeVersionUploadError } from '@/utils/apiError'
import type { VersionOut } from '@/types/api'

const props = defineProps<{ shotId: number }>()
const emit = defineEmits<{ uploaded: [version: VersionOut] }>()

const ALLOWED_EXTENSIONS = ['mp4', 'jpg', 'jpeg', 'png']

const store = useVersionsStore()
const message = useMessage()

const fileInput = ref<HTMLInputElement | null>(null)
const isBusy = computed(() => store.uploadState !== 'idle')

function pickFile() {
  fileInput.value?.click()
}

async function handleFileChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset so choosing the same file again (after a failure) still fires.
  input.value = ''
  if (!file) return

  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    message.error('Поддерживаются файлы mp4 (h264), jpg и png.')
    return
  }

  try {
    const version = await store.upload(props.shotId, file)
    emit('uploaded', version)
  } catch (error) {
    message.error(describeVersionUploadError(error))
  }
}
</script>

<template>
  <div class="version-upload">
    <p class="version-upload__hint">Поддерживаются mp4 (h264), jpg и png. Один файл за раз.</p>

    <div class="version-upload__controls">
      <n-button type="primary" :disabled="isBusy" @click="pickFile">
        <template #icon><n-icon :component="CloudUploadOutline" /></template>
        Выбрать файл
      </n-button>
      <input
        ref="fileInput"
        class="version-upload__file-input"
        type="file"
        accept=".mp4,.jpg,.jpeg,.png,video/mp4,image/jpeg,image/png"
        @change="handleFileChosen"
      />
      <n-progress
        v-if="store.uploadState === 'uploading'"
        type="line"
        :percentage="store.uploadProgress"
        :height="12"
        class="version-upload__progress"
      />
      <span v-else-if="store.uploadState === 'processing'" class="version-upload__processing">
        Файл отправлен, идёт обработка…
      </span>
    </div>
  </div>
</template>

<style scoped>
.version-upload {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.version-upload__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.version-upload__controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.version-upload__file-input {
  display: none;
}

.version-upload__progress {
  flex: 1;
  max-width: 320px;
}

.version-upload__processing {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}
</style>
