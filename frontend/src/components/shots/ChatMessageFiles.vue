<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { DocumentOutline, ImageOutline } from '@vicons/ionicons5'
import { formatFileSize } from '@/utils/format'
import type { AttachmentOut, VersionOut } from '@/types/api'

const props = defineProps<{ attachments: AttachmentOut[]; versions: VersionOut[] }>()

const images = computed(() =>
  props.attachments.filter((attachment) => attachment.content_type.startsWith('image/')),
)
const otherFiles = computed(() =>
  props.attachments.filter((attachment) => !attachment.content_type.startsWith('image/')),
)

function versionHref(version: VersionOut): string {
  return version.converted ?? version.source
}
</script>

<template>
  <div v-if="attachments.length > 0 || versions.length > 0" class="chat-files">
    <div v-if="versions.length > 0" class="chat-files__row">
      <a
        v-for="version in versions"
        :key="version.id"
        class="chat-files__version"
        :href="versionHref(version)"
        target="_blank"
        rel="noopener"
      >
        <span class="chat-files__version-thumb">
          <img v-if="version.thumb" :src="version.thumb" :alt="version.name" loading="lazy" />
          <n-icon v-else :component="ImageOutline" :size="20" />
        </span>
        <span class="mono">{{ version.name }}</span>
      </a>
    </div>

    <div v-if="images.length > 0" class="chat-files__row">
      <a
        v-for="image in images"
        :key="image.id"
        class="chat-files__image"
        :href="image.url"
        target="_blank"
        rel="noopener"
        :title="image.filename"
      >
        <img :src="image.url" :alt="image.filename" loading="lazy" />
      </a>
    </div>

    <div v-if="otherFiles.length > 0" class="chat-files__row">
      <a
        v-for="file in otherFiles"
        :key="file.id"
        class="chat-files__file"
        :href="file.url"
        target="_blank"
        rel="noopener"
      >
        <n-icon :component="DocumentOutline" />
        <span>{{ file.filename }} · {{ formatFileSize(file.size) }}</span>
      </a>
    </div>
  </div>
</template>

<style scoped>
.chat-files {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.chat-files__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chat-files__version,
.chat-files__file {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 2px var(--space-2) 2px 2px;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 6px;
  color: inherit;
  font-size: var(--text-sm, 13px);
  text-decoration: none;
}

.chat-files__file {
  padding: 4px var(--space-2);
}

.chat-files__version-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 27px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--color-surface-muted, rgba(128, 128, 128, 0.12));
}

.chat-files__version-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chat-files__image img {
  display: block;
  max-width: 240px;
  max-height: 160px;
  border-radius: 6px;
}
</style>
