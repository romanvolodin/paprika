import router from '@/router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const instance = axios.create({
  timeout: 30000,
  baseURL: import.meta.env.VITE_API_URL,
})

const token = localStorage.getItem('token') || null
if (token) {
  instance.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.data?.code === 'token_not_valid' && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Попытка обновить токен
        const authStore = useAuthStore()
        const newToken = await authStore.refreshAccessToken()

        // Повторяем оригинальный запрос
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return instance(originalRequest)
      } catch (refreshError) {
        // Если обновление не удалось, выходим из системы
        const authStore = useAuthStore()
        authStore.logout()
        router.push('/login')
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  },
)

export default instance
