<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotGroupsSection from '@/components/shots/ShotGroupsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useProjectPageStore } from '@/stores/projectPage'

const store = useProjectPageStore()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)
</script>

<template>
  <section v-if="store.project" class="project-groups">
    <h2 class="project-groups__heading">Группы кадров</h2>
    <shot-groups-section :project-id="store.project.id" :can-write="can(PERMISSION.groupManage)" />
  </section>
</template>

<style scoped>
.project-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 720px;
}

.project-groups__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}
</style>
