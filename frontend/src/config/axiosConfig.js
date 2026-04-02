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

let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
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

    // Исключаем запросы на обновление токена из обработки, чтобы избежать бесконечного цикла
    if (originalRequest.url?.includes('/api/token/refresh/')) {
      return Promise.reject(error)
    }

    if (error.response?.data?.code === 'token_not_valid') {
      if (originalRequest._retry) {
        // Уже пытались обновить, но не удалось - отклоняем запрос
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Если обновление уже в процессе, добавляем запрос в очередь
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return instance(originalRequest)
          })
          .catch(err => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Попытка обновить токен
        const authStore = useAuthStore()
        const newToken = await authStore.refreshAccessToken()

        isRefreshing = false
        processQueue(null, newToken)

        // Повторяем оригинальный запрос
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return instance(originalRequest)
      } catch (refreshError) {
        // Если обновление не удалось, выходим из системы
        isRefreshing = false
        processQueue(refreshError, null)

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
