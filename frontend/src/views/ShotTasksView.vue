<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotTasksSection from '@/components/shots/ShotTasksSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const store = useShotDetailStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)
</script>

<template>
  <div v-if="store.shot && store.project" class="shot-tasks">
    <shot-tasks-section
      :shot-id="store.shot.id"
      :project-id="store.project.id"
      :company-id="store.project.company_id"
      :members="store.members"
      :can-write="canWrite"
    />
  </div>
</template>

<style scoped>
.shot-tasks {
  max-width: 960px;
}
</style>
