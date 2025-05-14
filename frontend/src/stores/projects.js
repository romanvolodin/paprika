import axios from '@/config/axiosConfig'
import { defineStore } from 'pinia'

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    projects: [],
    currentProject: null,
    isLoading: false,
    errors: {},
  }),
  actions: {
    async fetchProjects() {
      if (this.projects.length > 0 || this.isLoading) return

      this.isLoading = true
      try {
        const response = await axios.get('/api/projects')
        this.projects = response.data.results
      } catch (error) {
        this.errors = error
      } finally {
        this.isLoading = false
      }
    },
  },
})
