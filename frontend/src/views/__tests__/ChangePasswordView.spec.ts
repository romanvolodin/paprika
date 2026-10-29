import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { NMessageProvider } from 'naive-ui'
import { AxiosError } from 'axios'
import ChangePasswordView from '@/views/ChangePasswordView.vue'
import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { MeOut } from '@/types/api'

vi.mock('@/api/auth')

function buildMe(overrides: Partial<MeOut> = {}): MeOut {
  return {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    is_superuser: false,
    must_change_password: false,
    ...overrides,
  }
}

const Host = defineComponent({
  setup() {
    return () => h(NMessageProvider, null, { default: () => h(ChangePasswordView) })
  },
})

async function mountPage(me: MeOut) {
  useAuthStore().currentUser = me
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/password', name: 'change-password', component: { render: () => null } },
      { path: '/projects', name: 'project-list', component: { render: () => null } },
      { path: '/login', name: 'login', component: { render: () => null } },
    ],
  })
  await router.push('/password')
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

async function typePasswords(
  wrapper: ReturnType<typeof mount>,
  current: string,
  next: string,
  again = next,
) {
  const inputs = wrapper.findAll('input')
  await inputs[0]!.setValue(current)
  await inputs[1]!.setValue(next)
  await inputs[2]!.setValue(again)
}

describe('ChangePasswordView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('explains a forced change and offers to sign out', async () => {
    const { wrapper } = await mountPage(buildMe({ must_change_password: true }))

    expect(wrapper.text()).toContain('временный пароль')
    expect(wrapper.text()).toContain('Выйти')
    expect(wrapper.text()).not.toContain('Назад')
  })

  it('is a plain change otherwise', async () => {
    const { wrapper } = await mountPage(buildMe())

    expect(wrapper.text()).toContain('Текущий пароль')
    expect(wrapper.text()).toContain('Назад')
  })

  it('cannot be sent while the two new passwords differ', async () => {
    const { wrapper } = await mountPage(buildMe())

    await typePasswords(wrapper, 'old-pass-1', 'new-pass-1', 'new-pass-2')

    expect(wrapper.text()).toContain('Пароли не совпадают')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('changes the password and goes to the projects', async () => {
    vi.mocked(authApi.changePassword).mockResolvedValue({} as never)
    const { wrapper, router } = await mountPage(buildMe({ must_change_password: true }))

    await typePasswords(wrapper, 'temporary', 'mine-now-1')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(authApi.changePassword).toHaveBeenCalledWith('temporary', 'mine-now-1')
    expect(useAuthStore().mustChangePassword).toBe(false)
    expect(router.currentRoute.value.name).toBe('project-list')
  })

  it('shows what the server said and stays when it refuses', async () => {
    const error = new AxiosError('bad', '400', undefined, undefined, {
      status: 400,
      data: {
        detail: [{ msg: 'Пароль слишком простой.', loc: ['new_password'], type: 'value_error' }],
      },
    } as never)
    vi.mocked(authApi.changePassword).mockRejectedValue(error)
    const { wrapper, router } = await mountPage(buildMe({ must_change_password: true }))

    await typePasswords(wrapper, 'temporary', '12345678')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('change-password')
    expect(useAuthStore().mustChangePassword).toBe(true)
  })

  it('signs out from the forced page', async () => {
    vi.mocked(authApi.logout).mockResolvedValue({} as never)
    const { wrapper, router } = await mountPage(buildMe({ must_change_password: true }))

    const button = wrapper.findAll('button').find((b) => b.text() === 'Выйти')
    await button!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('login')
    expect(useAuthStore().isAuthenticated).toBe(false)
  })
})
