<script setup lang="ts">
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { NTag } from 'naive-ui'
import type { ProjectOut } from '@/types/api'

defineProps<{
  project: ProjectOut
  to?: RouteLocationRaw
}>()
</script>

<template>
  <component :is="to ? RouterLink : 'div'" v-bind="to ? { to } : {}" class="project-card">
    <n-tag
      class="project-card__status"
      size="small"
      round
      :type="project.is_active ? 'success' : 'default'"
    >
      {{ project.is_active ? 'Активен' : 'Архив' }}
    </n-tag>

    <div class="project-card__cover">
      <img v-if="project.cover" :src="project.cover" :alt="project.name" loading="lazy" />
      <span v-else class="project-card__no-cover">Нет обложки</span>
    </div>

    <div class="project-card__info">
      <div class="project-card__heading">
        <span class="project-card__name">{{ project.name }}</span>
        <span class="project-card__code mono">{{ project.code }}</span>
      </div>
      <p v-if="project.description" class="project-card__description">
        {{ project.description }}
      </p>
    </div>
  </component>
</template>

<style scoped>
.project-card {
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

.project-card:hover {
  border-color: var(--color-border-strong);
  background: var(--color-bg-hover);
}

.project-card__status {
  position: absolute;
  top: 5px;
  right: 5px;
  background-color: #00000055;
  backdrop-filter: blur(100px);
}

.project-card__cover {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 16 / 9;
  background: var(--color-border);
}

.project-card__cover img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.project-card__no-cover {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm, 13px);
}

.project-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2);
}

.project-card__heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.project-card__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.project-card__code {
  flex-shrink: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.project-card__description {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}
</style>
