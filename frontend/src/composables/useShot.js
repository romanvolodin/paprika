import { ref } from 'vue'
import axios from '@/config/axiosConfig'

export function useShot(projectCode, shotName) {
  if (!projectCode || !shotName) {
    throw new Error('projectCode и shotName обязательны')
  }

  const shot = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  const fetchShot = async () => {
    isLoading.value = true
    error.value = null // сброс ошибки перед запросом

    try {
      const response = await axios.get(`/api/projects/${projectCode}/shots/${shotName}/`)
      shot.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка загрузки шота'
    } finally {
      isLoading.value = false
    }
  }

  return {
    shot,
    isLoading,
    error,
    fetchShot,
  }
}
