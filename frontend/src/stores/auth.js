import axios from '@/config/axiosConfig'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    refreshToken: localStorage.getItem('refreshToken') || null,
    user: JSON.parse(localStorage.getItem('user')) || null,
    isUserAuthenticated: !!(localStorage.getItem('token') && localStorage.getItem('refreshToken')),
  }),
  actions: {
    setToken(token) {
      this.isUserAuthenticated = true
      localStorage.setItem('token', token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    setRefreshToken(refreshToken) {
      localStorage.setItem('refreshToken', refreshToken)
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
        const refreshToken = response.data.refresh
        this.setToken(token)
        this.setRefreshToken(refreshToken)
        await this.fetchUser()
        return true
      } catch (error) {
        throw error.response?.data.detail
      }
    },

    async refreshAccessToken() {
      try {
        const refreshToken = localStorage.getItem('refreshToken')
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        const response = await axios.post('/api/token/refresh/', { refresh: refreshToken })
        const newToken = response.data.access
        this.setToken(newToken)
        return newToken
      } catch (error) {
        console.error('Token refresh failed', error)
        this.logout()
        throw error
      }
    },

    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      this.user = null
      this.isUserAuthenticated = false
      delete axios.defaults.headers.common['Authorization']
    },
  },
})
