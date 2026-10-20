<script setup lang="ts">
import { storeToRefs } from 'pinia'
import ShotGroupsSection from '@/components/shots/ShotGroupsSection.vue'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useProjectPageStore } from '@/stores/projectPage'

const store = useProjectPageStore()
const { members } = storeToRefs(store)
const { canWrite } = useProjectPermissions(members)
</script>

<template>
  <section v-if="store.project" class="project-groups">
    <h2 class="project-groups__heading">Группы кадров</h2>
    <shot-groups-section :project-id="store.project.id" :can-write="canWrite" />
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
