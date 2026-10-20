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
    <shot-chat-section :shot-id="store.shot.id" :can-write="canWrite" />
  </div>
</template>

<style scoped>
.shot-review {
  max-width: 960px;
}
</style>
