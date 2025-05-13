import axios from '@/config/axiosConfig'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    user: JSON.parse(localStorage.getItem('user')) || null,
    isUserAuthenticated: !!localStorage.getItem('token'),
  }),
  actions: {
    setToken(token) {
      this.isUserAuthenticated = true
      localStorage.setItem('token', token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    setUser(user) {
      this.user = user
      localStorage.setItem('user', JSON.stringify(user))
    },

    async fetchUser() {
      try {
        const response = await axios.get('/api/me/')
        this.setUser(response.data)
      } catch (error) {
        console.error('Failed to fetch user', error)
        this.logout()
      }
    },

    async login(credentials) {
      try {
        const response = await axios.post('/api/token/', credentials)
        const token = response.data.access
        this.setToken(token)
        await this.fetchUser()
        return true
      } catch (error) {
        console.error('Login failed', error)
        return false
      }
    },

    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      this.user = null
      this.isUserAuthenticated = false
      delete axios.defaults.headers.common['Authorization']
    },
  },
})
