<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import ShotStatusTag from '@/components/shots/ShotStatusTag.vue'
import type { ShotOut, ShotStatusOut } from '@/types/api'

defineProps<{
  shot: ShotOut
  status?: ShotStatusOut
  to: RouteLocationRaw
}>()
</script>

<template>
  <RouterLink class="shot-card" :to="to">
    <shot-status-tag class="status" v-if="status" :status="status" />

    <div class="shot-card__preview">
      <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" loading="lazy" />
      <span v-else class="shot-card__no-preview">Нет превью</span>
    </div>

    <div class="shot-card__info">
      <div class="shot-card__heading">
        <span class="shot-card__name mono">{{ shot.name }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.shot-card {
  position: relative;
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

.status {
  position: absolute;
  top: 5px;
  right: 5px;
  background-color: #00000055;
  backdrop-filter: blur(100px);
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
  padding: var(--space-1);
  padding-left: var(--space-2);
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
</style>
