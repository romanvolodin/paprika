<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import UserAvatar from '@/components/common/UserAvatar.vue'
import ChatMessageFiles from '@/components/shots/ChatMessageFiles.vue'
import { describeEventAction, formatClock, userName } from '@/utils/chat'
import type { FeedItemOut } from '@/types/api'

const props = defineProps<{ item: FeedItemOut; companySlug: string; projectCode: string }>()

const shotParams = computed(() => ({
  companySlug: props.companySlug,
  projectCode: props.projectCode,
  shotName: props.item.shot.name,
}))

const action = computed(() => {
  switch (props.item.type) {
    case 'chat':
      return 'написал в чате'
    case 'version':
      return 'загрузил версию'
    default:
      return describeEventAction(props.item.event, props.item.payload)
  }
})

const version = computed(() => props.item.version)
</script>

<template>
  <article class="feed-row">
    <time class="feed-row__time" :datetime="item.created_at">{{
      formatClock(item.created_at)
    }}</time>

    <div class="feed-row__body">
      <p class="feed-row__line">
        <UserAvatar :user="item.created_by" :size="18" />
        <strong class="feed-row__author">{{ userName(item.created_by) }}</strong>
        <span class="feed-row__action">{{ action }}</span>

        <template v-if="item.type === 'version' && version">
          <RouterLink
            class="feed-row__link mono"
            :to="{ name: 'shot-detail', params: shotParams, query: { version: version.name } }"
          >
            {{ version.name }}
          </RouterLink>
        </template>

        <template v-else-if="item.type === 'chat'">
          <RouterLink class="feed-row__link mono" :to="{ name: 'shot-detail', params: shotParams }">
            {{ item.shot.name }}
          </RouterLink>
          <span v-if="item.text" class="feed-row__text">: {{ item.text }}</span>
        </template>

        <template v-else>
          <span class="feed-row__action">·</span>
          <RouterLink class="feed-row__link mono" :to="{ name: 'shot-detail', params: shotParams }">
            {{ item.shot.name }}
          </RouterLink>
        </template>
      </p>

      <a
        v-if="item.type === 'version' && version"
        class="feed-row__thumb"
        :href="version.converted ?? version.source"
        target="_blank"
        rel="noopener"
        :title="version.name"
      >
        <img v-if="version.thumb" :src="version.thumb" :alt="version.name" loading="lazy" />
      </a>

      <ChatMessageFiles
        v-if="item.type === 'chat'"
        :attachments="item.attachments"
        :versions="item.versions"
      />
    </div>
  </article>
</template>

<style scoped>
.feed-row {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
}

.feed-row__time {
  flex: none;
  width: 44px;
  padding-top: 2px;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm, 13px);
}

.feed-row__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.feed-row__line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  margin: 0;
  white-space: nowrap;
}

.feed-row__author {
  flex: none;
}

.feed-row__action {
  flex: none;
  color: var(--color-text-secondary);
}

.feed-row__link {
  flex: none;
  color: var(--color-accent);
  text-decoration: none;
}

.feed-row__link:hover {
  text-decoration: underline;
}

.feed-row__text {
  min-width: 0;
  margin-left: -4px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-row__thumb {
  display: flex;
  width: 160px;
  height: 90px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-bg-elevated);
}

.feed-row__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
