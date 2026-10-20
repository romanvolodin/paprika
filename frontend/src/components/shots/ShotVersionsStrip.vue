<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute, type RouteLocationRaw } from 'vue-router'
import type { VersionOut } from '@/types/api'

const props = defineProps<{
  versions: VersionOut[]
  // The version being played, framed in the strip.
  currentId: number | null
  canWrite: boolean
  uploadTo: RouteLocationRaw
}>()

const route = useRoute()
const stripRef = ref<HTMLElement | null>(null)

// A version is picked by putting its name into the address; other
// parts of the query stay as they are.
function versionTo(version: VersionOut): RouteLocationRaw {
  return { query: { ...route.query, version: version.name } }
}

// The framed version may be far along the strip (opened by a link).
watch(
  () => [props.currentId, props.versions] as const,
  async () => {
    await nextTick()
    stripRef.value
      ?.querySelector('[aria-current="true"]')
      ?.scrollIntoView?.({ inline: 'nearest', block: 'nearest' })
  },
)
</script>

<template>
  <nav ref="stripRef" class="versions-strip" aria-label="Версии кадра">
    <RouterLink v-if="canWrite" class="versions-strip__upload" :to="uploadTo">
      Загрузить версию
    </RouterLink>

    <RouterLink
      v-for="version in versions"
      :key="version.id"
      class="versions-strip__item"
      :class="{ 'versions-strip__item--active': version.id === currentId }"
      :to="versionTo(version)"
      :aria-current="version.id === currentId ? 'true' : undefined"
    >
      <img v-if="version.thumb" :src="version.thumb" :alt="version.name" loading="lazy" />
      <span class="versions-strip__name mono">{{ version.name }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.versions-strip {
  display: flex;
  gap: var(--space-2);
  padding-bottom: var(--space-1);
  overflow-x: auto;
}

.versions-strip__upload,
.versions-strip__item {
  flex: none;
  height: 100px;
  border-radius: var(--radius-sm);
}

.versions-strip__upload {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 140px;
  border: 1px dashed var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  text-align: center;
  text-decoration: none;
}

.versions-strip__upload:hover {
  color: var(--color-text);
}

.versions-strip__item {
  position: relative;
  width: 178px;
  border: 2px solid transparent;
  background: var(--color-border);
  overflow: hidden;
}

.versions-strip__item--active {
  border-color: var(--color-accent);
}

.versions-strip__item img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.versions-strip__name {
  position: absolute;
  top: var(--space-1);
  right: var(--space-2);
  left: var(--space-2);
  overflow: hidden;
  color: #fff;
  font-size: 12px;
  text-overflow: ellipsis;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}
</style>
