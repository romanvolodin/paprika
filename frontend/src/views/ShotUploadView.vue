<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import ShotVersionUpload from '@/components/shots/ShotVersionUpload.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useShotDetailStore } from '@/stores/shotDetail'
import type { VersionOut } from '@/types/api'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useShotDetailStore()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)
const canUpload = computed(() => can(PERMISSION.versionUpload))

// After an upload the new version is what the reader wants to see.
function handleUploaded(version: VersionOut) {
  message.success('Версия загружена.')
  router.push({
    name: 'shot-detail',
    params: route.params,
    query: { version: version.name },
  })
}
</script>

<template>
  <div v-if="store.shot && store.project" class="shot-upload">
    <shot-version-upload
      v-if="canUpload"
      :shot-id="store.shot.id"
      :project-id="store.project.id"
      :company-id="store.project.company_id"
      @uploaded="handleUploaded"
    />
    <p v-else class="shot-upload__note">У вас нет прав загружать версии в этот проект.</p>
  </div>
</template>

<style scoped>
.shot-upload {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.shot-upload__note {
  margin: 0;
  color: var(--color-text-secondary);
}
</style>
