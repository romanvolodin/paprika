<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const store = useShotDetailStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)
</script>

<template>
  <div v-if="store.shot" class="shot-versions">
    <shot-versions-section :shot-id="store.shot.id" :can-write="canWrite" />
  </div>
</template>

<style scoped>
.shot-versions {
  max-width: 960px;
}
</style>
