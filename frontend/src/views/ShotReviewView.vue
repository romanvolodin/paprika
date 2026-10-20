<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotChatSection from '@/components/shots/ShotChatSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const store = useShotDetailStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)
</script>

<template>
  <div v-if="store.shot" class="shot-review">
    <div class="shot-review__main">
      <div class="shot-review__player" data-test="player">Плеер</div>
      <div class="shot-review__versions" data-test="versions-strip">Лента версий</div>
    </div>

    <aside class="shot-review__chat" data-test="chat">
      <shot-chat-section :shot-id="store.shot.id" :can-write="canWrite" />
    </aside>
  </div>
</template>

<style scoped>
.shot-review {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: var(--space-4);
  min-height: 0;
}

.shot-review__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 0;
}

.shot-review__player,
.shot-review__versions {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.shot-review__player {
  flex: 1;
  min-height: 0;
}

.shot-review__versions {
  flex: none;
  height: 120px;
}

.shot-review__chat {
  min-height: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

/* On a narrow screen the columns stack and the page scrolls. */
@media (max-width: 900px) {
  .shot-review {
    flex: none;
    grid-template-columns: minmax(0, 1fr);
  }

  .shot-review__player {
    flex: none;
    aspect-ratio: 16 / 9;
  }

  .shot-review__chat {
    height: 520px;
  }
}
</style>
