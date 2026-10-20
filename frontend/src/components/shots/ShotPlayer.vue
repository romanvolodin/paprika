<script setup lang="ts">
import { computed } from 'vue'
import type { ShotReviewState } from '@/stores/shotReview'
import type { VersionOut } from '@/types/api'

const props = defineProps<{
  state: ShotReviewState
  version: VersionOut | null
  // The version name asked for in the address, to name it in the
  // "not found" note.
  requestedName: string | null
}>()

const mediaUrl = computed(() => props.version?.converted ?? props.version?.source ?? '')

const note = computed(() => {
  switch (props.state) {
    case 'loading':
      return 'Загрузка…'
    case 'empty':
      return 'В кадре пока нет версий.'
    case 'not-found':
      return `Версия ${props.requestedName ?? ''} не найдена.`
    case 'error':
      return 'Не удалось загрузить версии.'
    default:
      return null
  }
})
</script>

<template>
  <div class="shot-player">
    <p v-if="note" class="shot-player__note">{{ note }}</p>

    <!-- Browsers only allow autoplay without sound, hence `muted`. The
         key makes a new element (and a new autoplay) per version. -->
    <video
      v-else-if="version && version.type === 'video'"
      :key="version.id"
      class="shot-player__media"
      :src="mediaUrl"
      :poster="version.thumb ?? undefined"
      controls
      autoplay
      muted
      loop
      playsinline
    />

    <img
      v-else-if="version"
      :key="version.id"
      class="shot-player__media"
      :src="mediaUrl"
      :alt="version.name"
    />
  </div>
</template>

<style scoped>
.shot-player {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: #000;
}

.shot-player__note {
  margin: 0;
  color: var(--color-text-secondary);
}

.shot-player__media {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
