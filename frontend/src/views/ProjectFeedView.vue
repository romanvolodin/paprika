<script setup lang="ts">
import { computed, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NIcon,
  NPopover,
  NRadio,
  NRadioGroup,
  NSpace,
} from 'naive-ui'
import { ChevronDownOutline } from '@vicons/ionicons5'
import FeedEventRow from '@/components/feed/FeedEventRow.vue'
import { useProjectFeedStore, FEED_EVENT_TYPES, type FeedScope } from '@/stores/projectFeed'
import { useProjectPageStore } from '@/stores/projectPage'
import { describeTypeFilter, FEED_TYPE_LABELS, groupFeedByDay } from '@/utils/feed'
import type { FeedEventType } from '@/types/api'

const page = useProjectPageStore()
const feed = useProjectFeedStore()

watch(
  () => page.project?.id,
  (projectId) => {
    if (projectId !== undefined) feed.open(projectId)
  },
  { immediate: true },
)

const days = computed(() => groupFeedByDay(feed.items))
const typesLabel = computed(() => describeTypeFilter(feed.types))

// The checkboxes show every box ticked while no filter is set.
const checkedTypes = computed(() => (feed.types.length === 0 ? FEED_EVENT_TYPES : feed.types))

function changeScope(value: FeedScope) {
  feed.setScope(value)
}

function changeTypes(value: Array<string | number>) {
  feed.setTypes(value as FeedEventType[])
}
</script>

<template>
  <section class="project-feed">
    <header class="project-feed__header">
      <h2 class="project-feed__title">Лента событий</h2>

      <n-space align="center" :size="8">
        <n-button text size="small" :disabled="feed.isDefaultFilter" @click="feed.resetFilters()">
          Сбросить
        </n-button>

        <n-popover trigger="click" placement="bottom-end" :show-arrow="false">
          <template #trigger>
            <n-button size="small" :type="feed.scope === 'mine' ? 'primary' : 'default'" secondary>
              {{ feed.scope === 'mine' ? 'По моим кадрам' : 'По всему проекту' }}
              <template #icon><n-icon :component="ChevronDownOutline" /></template>
            </n-button>
          </template>
          <n-radio-group :value="feed.scope" name="feed-scope" @update:value="changeScope">
            <n-space vertical :size="8">
              <n-radio value="project">По всему проекту</n-radio>
              <n-radio value="mine">По моим кадрам</n-radio>
            </n-space>
          </n-radio-group>
        </n-popover>

        <n-popover trigger="click" placement="bottom-end" :show-arrow="false">
          <template #trigger>
            <n-button size="small" :type="feed.types.length > 0 ? 'primary' : 'default'" secondary>
              {{ typesLabel }}
              <template #icon><n-icon :component="ChevronDownOutline" /></template>
            </n-button>
          </template>
          <n-checkbox-group :value="checkedTypes" @update:value="changeTypes">
            <n-space vertical :size="8">
              <n-checkbox v-for="type in FEED_EVENT_TYPES" :key="type" :value="type">
                {{ FEED_TYPE_LABELS[type] }}
              </n-checkbox>
            </n-space>
          </n-checkbox-group>
        </n-popover>
      </n-space>
    </header>

    <p v-if="feed.state === 'loading'" class="project-feed__message">Загружаем ленту…</p>
    <p v-else-if="feed.state === 'error'" class="project-feed__message">
      Не удалось загрузить ленту.
      <n-button text type="primary" @click="feed.resetFilters()">Попробовать снова</n-button>
    </p>
    <p v-else-if="feed.items.length === 0" class="project-feed__message">
      За это время ничего не происходило.
    </p>

    <template v-else-if="page.company && page.project">
      <div v-for="day in days" :key="day.label" class="project-feed__day">
        <h3 class="project-feed__day-label">{{ day.label }}</h3>
        <FeedEventRow
          v-for="item in day.items"
          :key="item.key"
          :item="item"
          :company-slug="page.company.slug"
          :project-code="page.project.code"
        />
      </div>

      <div v-if="feed.hasMore" class="project-feed__more">
        <n-button :loading="feed.isLoadingMore" @click="feed.loadMore()">Загрузить еще</n-button>
        <span v-if="feed.loadMoreFailed" class="project-feed__message">
          Не удалось загрузить. Попробуйте ещё раз.
        </span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.project-feed {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 860px;
}

.project-feed__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.project-feed__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.project-feed__message {
  color: var(--color-text-secondary);
}

.project-feed__day-label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-3) 0 var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  font-weight: 600;
}

.project-feed__day-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.project-feed__more {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}
</style>
