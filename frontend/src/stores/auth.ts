import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as authApi from '@/api/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import type { MeOut } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  // Both tokens live in httponly cookies now - the browser sends and
  // stores them on its own, and JavaScript can't read them even to
  // check whether they exist. `currentUser` is the only signal we have
  // left for "am I logged in".
  const currentUser = ref<MeOut | null>(null)

  const isAuthenticated = computed(() => currentUser.value !== null)
  const isSuperuser = computed(() => currentUser.value?.is_superuser ?? false)
  // An account created with a temporary password can only change it.
  const mustChangePassword = computed(() => currentUser.value?.must_change_password ?? false)

  function clearSession() {
    currentUser.value = null
    useCurrentCompanyStore().reset()
  }

  async function login(email: string, password: string) {
    currentUser.value = await authApi.login(email, password)
  }

  /** Exchange the refresh cookie for a new pair and refresh `currentUser`. */
  async function refresh(): Promise<void> {
    currentUser.value = await authApi.refresh()
  }

  /** Restore a session from the refresh cookie, e.g. on app load. */
  async function restoreSession() {
    if (currentUser.value) return
    try {
      await refresh()
    } catch {
      clearSession()
    }
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    await authApi.changePassword(currentPassword, newPassword)
    if (currentUser.value) {
      currentUser.value = { ...currentUser.value, must_change_password: false }
    }
  }

  async function logout() {
    clearSession()
    try {
      await authApi.logout()
    } catch {
      // Already logged out locally; a failed revoke call server-side
      // isn't worth surfacing to the user.
    }
  }

  return {
    currentUser,
    isAuthenticated,
    isSuperuser,
    mustChangePassword,
    login,
    changePassword,
    logout,
    refresh,
    restoreSession,
  }
})
