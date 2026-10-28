<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import ShotChatSection from '@/components/shots/ShotChatSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import ShotPlayer from '@/components/shots/ShotPlayer.vue'
import ShotVersionsStrip from '@/components/shots/ShotVersionsStrip.vue'
import { useShotDetailStore } from '@/stores/shotDetail'
import { useShotReviewStore } from '@/stores/shotReview'

const route = useRoute()
const store = useShotDetailStore()
const review = useShotReviewStore()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)

// The version to play lives in the address: `?version=<name>`.
const requestedName = computed(() => {
  const value = Array.isArray(route.query.version) ? route.query.version[0] : route.query.version
  return value ? value : null
})

const uploadTo = computed(() => ({ name: 'shot-upload', params: route.params }))

// Opening the shot (or coming back to this tab) loads the versions
// anew, so a version uploaded meanwhile shows up.
watch(
  () => store.shot?.id,
  (shotId) => {
    if (shotId !== undefined) review.load(shotId, requestedName.value)
  },
  { immediate: true },
)

watch(requestedName, (name) => {
  if (store.shot) review.select(store.shot.id, name)
})
</script>

<template>
  <div v-if="store.shot" class="shot-review">
    <div class="shot-review__main">
      <div class="shot-review__player" data-test="player">
        <shot-player
          :state="review.state"
          :version="review.current"
          :requested-name="requestedName"
        />
      </div>
      <div class="shot-review__versions" data-test="versions-strip">
        <shot-versions-strip
          :versions="review.versions"
          :current-id="review.current?.id ?? null"
          :can-upload="can(PERMISSION.versionUpload)"
          :upload-to="uploadTo"
        />
      </div>
    </div>

    <aside class="shot-review__chat" data-test="chat">
      <shot-chat-section
        :shot-id="store.shot.id"
        :can-write="can(PERMISSION.chatWrite)"
        :can-moderate="can(PERMISSION.chatEditAny)"
      />
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

.shot-review__player {
  flex: 1;
  min-height: 0;
}

.shot-review__versions {
  flex: none;
  min-width: 0;
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
