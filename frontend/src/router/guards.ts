import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'

export function setupAuthGuard(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()

    // On a hard reload the access token is gone (it's in-memory only)
    // but a refresh token may still be in localStorage - try to restore
    // the session before deciding whether this navigation is allowed.
    if (!auth.isAuthenticated) {
      await auth.restoreSession()
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }

    // Until the password is changed the API refuses everything else, so
    // there is nothing to show but the page that changes it.
    if (auth.mustChangePassword) {
      return to.name === 'change-password' ? true : { name: 'change-password' }
    }

    if (to.meta.requiresSuperuser && !auth.isSuperuser) {
      return { name: 'project-list' }
    }

    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'project-list' }
    }

    if (auth.isAuthenticated) {
      const currentCompany = useCurrentCompanyStore()
      if (!currentCompany.isInitialized) {
        await currentCompany.initialize()
      }
    }

    return true
  })
}
