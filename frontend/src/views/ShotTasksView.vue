<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotTasksSection from '@/components/shots/ShotTasksSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const store = useShotDetailStore()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)
</script>

<template>
  <div v-if="store.shot && store.project">
    <shot-tasks-section
      :shot-id="store.shot.id"
      :project-id="store.project.id"
      :company-id="store.project.company_id"
      :members="store.members"
      :can-create="can(PERMISSION.taskCreate)"
      :can-edit="can(PERMISSION.taskEdit)"
      :can-delete="can(PERMISSION.taskDelete)"
      :can-update-own="can(PERMISSION.taskUpdateOwn)"
    />
  </div>
</template>
