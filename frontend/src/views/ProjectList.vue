<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'

const router = useRouter()
const projectsStore = useProjectsStore()
const _projects = ref([])

function goToShots(project) {
  projectsStore.currentProject = project
  router.push({ name: 'shots-by-project', params: { projectCode: project.code } })
}

onMounted(async () => {
  await projectsStore.fetchProjects()
  _projects.value = projectsStore.projects
})
</script>

<template>
  <router-link :to="{ name: 'create-project' }">Создать проект</router-link>
  <div v-if="!!_projects" class="empty-message">
    <p>Проектов пока нет</p>
  </div>

  <div v-else class="projects-list">
    <div v-if="projectsStore.error" class="error-message">
      {{ projectsStore.error }}
    </div>
    <div v-else-if="projectsStore.isLoading" class="loading">Загрузка...</div>
    <div v-else class="projects-grid">
      <div
        v-for="project in _projects"
        :key="project.url"
        class="project-card"
        @click="goToShots(project)"
      >
        <img v-if="project.thumb" :src="project.thumb" :alt="project.code" class="project-image" />

        <div v-else class="project-no-thumb">Нет превью</div>

        <div class="project-info">
          {{ project.code }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  text-decoration: none;
}
.empty-message {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 90vh;
}

.projects-list {
  padding: 1rem;
}

.error-message {
  margin: 1rem 0;
  border: 1px solid #dc3545;
  border-radius: 4px;
  background-color: #f8d7da;
  padding: 1rem;
  color: #dc3545;
}

.loading {
  padding: 2rem;
  color: #666;
  font-size: 1.2rem;
  text-align: center;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 5px;
}

.project-card {
  transition: transform 0.1s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.project-card:hover {
  transform: translateY(-4px);
  border: 1px solid steelblue;
}

.project-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.project-no-thumb {
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #ddd;
  width: 100%;
  height: 200px;
  color: #999;
}

.project-info {
  padding: 2px 5px;
}
</style>
