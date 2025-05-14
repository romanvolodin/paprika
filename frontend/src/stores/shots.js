import axios from '@/config/axiosConfig'
import { defineStore } from 'pinia'

export const useShotsStore = defineStore('shots', {
  state: () => ({
    shots: [],
    currentShot: null,
    isLoading: false,
    errors: {},
  }),
  actions: {
    async fetchShots(project_code = null) {
      if (this.shots.length > 0 || this.isLoading) return

      this.isLoading = true

      let params = {}
      if (project_code) {
        params = { project: project_code }
      }

      try {
        const response = await axios.get('/api/shots', { params })
        this.shots = response.data.results
      } catch (error) {
        this.errors = error
      } finally {
        this.isLoading = false
      }
    },
  },
})
