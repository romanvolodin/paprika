import router from '@/router'
import axios from 'axios'

const instance = axios.create({
  timeout: 10000,
  baseURL: import.meta.env.VITE_API_URL,
})

const token = localStorage.getItem('token') || null
if (token) {
  instance.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.code === 'token_not_valid') {
      router.push('/login')
    }
    return Promise.reject(error)
  },
)

export default instance
