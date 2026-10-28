<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const route = useRoute()
const store = useShotDetailStore()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)

const uploadTo = computed(() => ({ name: 'shot-upload', params: route.params }))
</script>

<template>
  <div v-if="store.shot">
    <shot-versions-section
      :shot-id="store.shot.id"
      :can-upload="can(PERMISSION.versionUpload)"
      :can-delete="can(PERMISSION.versionDelete)"
      :can-delete-own="can(PERMISSION.versionDeleteOwn)"
      :upload-to="uploadTo"
    />
  </div>
</template>
