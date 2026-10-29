import { apiClient } from './client'
import type { MeOut } from '@/types/api'

export function login(email: string, password: string) {
  return apiClient.post<MeOut>('/auth/login/', { email, password }).then((res) => res.data)
}

// No request/response body: the browser sends the refresh cookie on its
// own, and the new one comes back as a `Set-Cookie` header.
export function refresh() {
  return apiClient.post<MeOut>('/auth/refresh/').then((res) => res.data)
}

export function logout() {
  return apiClient.post<null>('/auth/logout/')
}

export function changePassword(currentPassword: string, newPassword: string) {
  return apiClient.post<null>('/auth/password/', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
