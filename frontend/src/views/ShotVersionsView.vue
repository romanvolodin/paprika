<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const route = useRoute()
const store = useShotDetailStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)

const uploadTo = computed(() => ({ name: 'shot-upload', params: route.params }))
</script>

<template>
  <div v-if="store.shot">
    <shot-versions-section :shot-id="store.shot.id" :can-write="canWrite" :upload-to="uploadTo" />
  </div>
</template>
