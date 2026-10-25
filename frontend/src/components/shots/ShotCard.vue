<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import ShotStatusTag from '@/components/shots/ShotStatusTag.vue'
import type { ShotGroupOut, ShotOut, ShotStatusOut } from '@/types/api'

defineProps<{
  shot: ShotOut
  status?: ShotStatusOut
  groups: ShotGroupOut[]
  to: RouteLocationRaw
}>()
</script>

<template>
  <RouterLink class="shot-card" :to="to">
    <div class="shot-card__preview">
      <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" loading="lazy" />
      <span v-else class="shot-card__no-preview">Нет превью</span>
    </div>

    <div class="shot-card__info">
      <div class="shot-card__heading">
        <span class="shot-card__name mono">{{ shot.name }}</span>
        <shot-status-tag v-if="status" :status="status" />
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.shot-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--color-text);
  text-decoration: none;
  overflow: hidden;
  transition: var(--transition-theme);
}

.shot-card:hover {
  border-color: var(--color-border-strong);
  background: var(--color-bg-hover);
}

.shot-card__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 16 / 9;
  background: var(--color-border);
}

.shot-card__preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.shot-card__no-preview {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm, 13px);
}

.shot-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
}

.shot-card__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.shot-card__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shot-card__groups {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px);
}
</style>
