import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { NMessageProvider } from 'naive-ui'
import { AxiosError } from 'axios'
import InviteView from '@/views/InviteView.vue'
import * as authApi from '@/api/auth'
import * as companiesApi from '@/api/companies'
import * as invitationsApi from '@/api/invitations'
import { useAuthStore } from '@/stores/auth'
import type { InvitationInfoOut, MeOut } from '@/types/api'

vi.mock('@/api/auth')
vi.mock('@/api/companies')
vi.mock('@/api/invitations')

function info(overrides: Partial<InvitationInfoOut> = {}): InvitationInfoOut {
  return {
    email: 'invitee@paprika.dev',
    company_id: 7,
    company_name: 'Acme',
    role_name: 'Фрилансер',
    project_names: ['Фильм'],
    expires_at: '2099-01-01T00:00:00Z',
    status: 'pending',
    account_exists: false,
    ...overrides,
  }
}

function me(email: string): MeOut {
  return {
    id: 1,
    email,
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    is_superuser: false,
    must_change_password: false,
  }
}

const Host = defineComponent({
  setup() {
    return () => h(NMessageProvider, null, { default: () => h(InviteView, { token: 'tok' }) })
  },
})

async function mountPage(invitationInfo: InvitationInfoOut | 'missing', signedInAs?: string) {
  if (invitationInfo === 'missing') {
    vi.mocked(invitationsApi.getInviteInfo).mockRejectedValue(
      new AxiosError('nope', '404', undefined, undefined, { status: 404 } as never),
    )
  } else {
    vi.mocked(invitationsApi.getInviteInfo).mockResolvedValue(invitationInfo)
  }
  if (signedInAs) useAuthStore().currentUser = me(signedInAs)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/invite/:token', name: 'invite', component: { render: () => null } },
      { path: '/login', name: 'login', component: { render: () => null } },
      { path: '/projects', name: 'project-list', component: { render: () => null } },
    ],
  })
  await router.push('/invite/tok')
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll('button').find((button) => button.text().includes(text))
}

describe('InviteView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
  })

  it('says so when the link is not valid', async () => {
    const { wrapper } = await mountPage('missing')

    expect(wrapper.text()).toContain('недействительна')
  })

  it('tells what the invitation is for', async () => {
    const { wrapper } = await mountPage(info())

    expect(wrapper.text()).toContain('Acme')
    expect(wrapper.text()).toContain('Фрилансер')
    expect(wrapper.text()).toContain('Фильм')
  })

  it.each([
    ['expired', 'Срок приглашения истёк'],
    ['accepted', 'уже использовано'],
  ] as const)('says when it is %s and offers nothing', async (status, text) => {
    const { wrapper } = await mountPage(info({ status }))

    expect(wrapper.text()).toContain(text)
    expect(buttonByText(wrapper, 'Принять')).toBeUndefined()
    expect(buttonByText(wrapper, 'Создать аккаунт')).toBeUndefined()
  })

  describe('for an email without an account', () => {
    it('makes the account, signs in and goes to the app', async () => {
      vi.mocked(invitationsApi.registerByInvite).mockResolvedValue({} as never)
      vi.mocked(authApi.login).mockResolvedValue(me('invitee@paprika.dev'))
      const { wrapper, router } = await mountPage(info())

      const inputs = wrapper.findAll('input')
      await inputs[0]!.setValue('Анна')
      await inputs[1]!.setValue('Иванова')
      await inputs[2]!.setValue('a-fresh-passphrase-1')
      await inputs[3]!.setValue('a-fresh-passphrase-1')
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(invitationsApi.registerByInvite).toHaveBeenCalledWith('tok', {
        first_name: 'Анна',
        last_name: 'Иванова',
        password: 'a-fresh-passphrase-1',
      })
      expect(authApi.login).toHaveBeenCalledWith('invitee@paprika.dev', 'a-fresh-passphrase-1')
      expect(router.currentRoute.value.name).toBe('project-list')
    })

    it('does not send the form while the passwords differ', async () => {
      const { wrapper } = await mountPage(info())

      const inputs = wrapper.findAll('input')
      await inputs[0]!.setValue('Анна')
      await inputs[1]!.setValue('Иванова')
      await inputs[2]!.setValue('one-passphrase-1')
      await inputs[3]!.setValue('other-passphrase-2')

      expect(wrapper.text()).toContain('Пароли не совпадают')
      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    })
  })

  describe('for an email that has an account', () => {
    it('sends someone who is not signed in to the login, coming back here', async () => {
      const { wrapper, router } = await mountPage(info({ account_exists: true }))

      await buttonByText(wrapper, 'Войти')!.trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.name).toBe('login')
      expect(router.currentRoute.value.query.redirect).toBe('/invite/tok')
    })

    it('lets the signed-in owner of that email accept', async () => {
      vi.mocked(invitationsApi.acceptInvite).mockResolvedValue({} as never)
      const { wrapper, router } = await mountPage(
        info({ account_exists: true }),
        'Invitee@Paprika.dev',
      )

      await buttonByText(wrapper, 'Принять приглашение')!.trigger('click')
      await flushPromises()

      expect(invitationsApi.acceptInvite).toHaveBeenCalledWith('tok')
      expect(router.currentRoute.value.name).toBe('project-list')
    })

    it('tells someone signed in as another person to switch', async () => {
      const { wrapper } = await mountPage(info({ account_exists: true }), 'someone@else.dev')

      expect(wrapper.text()).toContain('someone@else.dev')
      expect(buttonByText(wrapper, 'Принять приглашение')).toBeUndefined()
      expect(buttonByText(wrapper, 'Выйти')).toBeDefined()
    })

    it('says so when the invitation was used in the meantime', async () => {
      vi.mocked(invitationsApi.acceptInvite).mockRejectedValue(
        new AxiosError('gone', '410', undefined, undefined, { status: 410 } as never),
      )
      const { wrapper, router } = await mountPage(
        info({ account_exists: true }),
        'invitee@paprika.dev',
      )

      await buttonByText(wrapper, 'Принять приглашение')!.trigger('click')
      await flushPromises()

      expect(router.currentRoute.value.name).toBe('invite')
    })
  })
})
