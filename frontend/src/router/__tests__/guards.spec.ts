import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { setupAuthGuard } from '@/router/guards'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import * as companiesApi from '@/api/companies'
import type { UserOut } from '@/types/api'

vi.mock('@/api/auth')
vi.mock('@/api/users')
vi.mock('@/api/companies')

const user: UserOut = {
  id: 1,
  email: 'roman@paprika.dev',
  first_name: 'Roman',
  last_name: 'Volodin',
  avatar: null,
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

function buildRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: { template: '<div />' }, meta: {} },
      {
        path: '/users',
        name: 'users-list',
        component: { template: '<div />' },
        meta: { requiresAuth: true },
      },
      {
        path: '/projects',
        name: 'project-list',
        component: { template: '<div />' },
        meta: { requiresAuth: true },
      },
    ],
  })
  setupAuthGuard(router)
  return router
}

describe('setupAuthGuard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Most guard tests aren't about the company switcher - give it an
    // empty, harmless default so authenticated navigations don't choke
    // on an unmocked response.
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
  })

  it('redirects an unauthenticated visitor away from a protected route, preserving the destination', async () => {
    const authApi = await import('@/api/auth')
    // No session cookie at all - the silent refresh attempt on this
    // first navigation should fail.
    vi.mocked(authApi.refresh).mockRejectedValue(new Error('401'))
    const router = buildRouter()

    await router.push('/users')

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/users')
  })

  it('lets an authenticated visitor through to a protected route', async () => {
    const router = buildRouter()
    const auth = useAuthStore()
    auth.currentUser = user

    await router.push('/users')

    expect(router.currentRoute.value.name).toBe('users-list')
  })

  it('redirects an already-authenticated visitor away from the login page', async () => {
    const router = buildRouter()
    const auth = useAuthStore()
    auth.currentUser = user

    await router.push('/login')

    expect(router.currentRoute.value.name).toBe('project-list')
  })

  it('lets an unauthenticated visitor reach the login page', async () => {
    const authApi = await import('@/api/auth')
    vi.mocked(authApi.refresh).mockRejectedValue(new Error('401'))
    const router = buildRouter()

    await router.push('/login')

    expect(router.currentRoute.value.name).toBe('login')
  })

  it('tries to restore a session from the refresh cookie before deciding', async () => {
    const authApi = await import('@/api/auth')
    vi.mocked(authApi.refresh).mockResolvedValue(user)

    const router = buildRouter()
    await router.push('/users')

    expect(authApi.refresh).toHaveBeenCalledWith()
    expect(router.currentRoute.value.name).toBe('users-list')
  })

  it('resolves the active company for an authenticated visitor without redirecting anywhere', async () => {
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [{ id: 1, name: 'Acme', slug: 'acme', created_at: '', updated_at: '' }],
      total: 1,
      page: 1,
      page_size: 100,
    })

    const router = buildRouter()
    const auth = useAuthStore()
    auth.currentUser = user

    await router.push('/users')

    const currentCompany = useCurrentCompanyStore()
    expect(router.currentRoute.value.name).toBe('users-list')
    expect(currentCompany.isInitialized).toBe(true)
    expect(currentCompany.currentCompanyId).toBe(1)
  })

  it('does not re-fetch companies on a second navigation once already initialized', async () => {
    const router = buildRouter()
    const auth = useAuthStore()
    auth.currentUser = user

    await router.push('/users')
    await router.push('/login')
    await router.push('/users')

    expect(companiesApi.listCompanies).toHaveBeenCalledTimes(1)
  })
})
