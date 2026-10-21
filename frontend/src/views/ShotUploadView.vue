<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import ShotVersionUpload from '@/components/shots/ShotVersionUpload.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'
import type { VersionOut } from '@/types/api'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useShotDetailStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)

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
  <div v-if="store.shot" class="shot-upload">
    <h2 class="shot-upload__heading">Загрузить версию</h2>

    <shot-version-upload v-if="canWrite" :shot-id="store.shot.id" @uploaded="handleUploaded" />
    <p v-else class="shot-upload__note">У вас нет прав загружать версии в этот проект.</p>
  </div>
</template>

<style scoped>
.shot-upload {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-upload__heading {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.shot-upload__note {
  margin: 0;
  color: var(--color-text-secondary);
}
</style>
