import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider, NSelect } from 'naive-ui'
import CompanyInvitationsSection from '@/components/company/CompanyInvitationsSection.vue'
import * as invitationsApi from '@/api/invitations'
import * as projectsApi from '@/api/projects'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import type { InvitationOut, ProjectOut, RoleOut } from '@/types/api'

vi.mock('@/api/invitations')
vi.mock('@/api/projects')

function role(id: number, name: string): RoleOut {
  return {
    id,
    company_id: 7,
    name,
    color: '#888888',
    permissions: [],
    sees_all_projects: false,
    company_members_count: 0,
    project_members_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function invitation(overrides: Partial<InvitationOut> = {}): InvitationOut {
  return {
    id: 1,
    company_id: 7,
    email: 'invited@paprika.dev',
    role: { id: 4, name: 'Исполнитель', color: '#E971B8' },
    projects: [],
    token: 'tok-1',
    expires_at: '2099-01-01T00:00:00Z',
    is_expired: false,
    created_by_name: 'Роман',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const Host = defineComponent({
  setup() {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () => h(CompanyInvitationsSection, { companyId: 7 }),
          }),
      })
  },
})

async function mountSection(existing: InvitationOut[] = []) {
  vi.mocked(invitationsApi.listCompanyInvitations).mockResolvedValue({ items: existing })
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items: [{ id: 3, name: 'Фильм' } as ProjectOut],
    total: 1,
    page: 1,
    page_size: 100,
  })
  const store = useCompanyDetailStore()
  store.roles = [role(4, 'Исполнитель'), role(5, 'Клиент')]
  const wrapper = mount(Host)
  await flushPromises()
  return wrapper
}

describe('CompanyInvitationsSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('lists the open invitations with their role and term', async () => {
    const wrapper = await mountSection([
      invitation(),
      invitation({ id: 2, email: 'old@paprika.dev', is_expired: true }),
    ])

    const items = wrapper.findAll('.invitations__item').map((item) => item.text())
    expect(items[0]).toContain('invited@paprika.dev')
    expect(items[0]).toContain('Исполнитель')
    expect(items[0]).toContain('до ')
    expect(items[1]).toContain('Истекло')
    expect(items[1]).toContain('Отправить снова')
    expect(items[1]).not.toContain('Копировать ссылку')
  })

  it('invites by email with a role and shows the link to pass on', async () => {
    vi.mocked(invitationsApi.createCompanyInvitation).mockResolvedValue(
      invitation({ email: 'new@paprika.dev', token: 'fresh-token' }),
    )
    const wrapper = await mountSection()

    await wrapper.find('.invitations__email input').setValue(' new@paprika.dev ')
    wrapper.findAllComponents(NSelect)[0]!.vm.$emit('update:value', 5)
    await wrapper.vm.$nextTick()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(invitationsApi.createCompanyInvitation).toHaveBeenCalledWith(7, {
      email: 'new@paprika.dev',
      role_id: 5,
      projects: [],
    })
    expect(wrapper.find('.invitations__result').text()).toContain('new@paprika.dev')
    expect(wrapper.find<HTMLInputElement>('.invitations__result input').element.value).toContain(
      '/invite/fresh-token',
    )
  })

  it('asks for a role in the projects once some are picked, and sends them', async () => {
    vi.mocked(invitationsApi.createCompanyInvitation).mockResolvedValue(invitation())
    const wrapper = await mountSection()
    expect(wrapper.findAllComponents(NSelect)).toHaveLength(2)

    await wrapper.find('.invitations__email input').setValue('new@paprika.dev')
    const [companyRole, projects] = wrapper.findAllComponents(NSelect)
    companyRole!.vm.$emit('update:value', 5)
    projects!.vm.$emit('update:value', [3])
    await wrapper.vm.$nextTick()
    expect(wrapper.findAllComponents(NSelect)).toHaveLength(3)
    wrapper.findAllComponents(NSelect)[2]!.vm.$emit('update:value', 4)
    await wrapper.vm.$nextTick()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(invitationsApi.createCompanyInvitation).toHaveBeenCalledWith(7, {
      email: 'new@paprika.dev',
      role_id: 5,
      projects: [{ project_id: 3, role_id: 4 }],
    })
  })

  it('cannot be sent without a role', async () => {
    const wrapper = await mountSection()

    await wrapper.find('.invitations__email input').setValue('new@paprika.dev')

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('renews an invitation and shows the new link', async () => {
    vi.mocked(invitationsApi.renewInvitation).mockResolvedValue(invitation({ token: 'renewed' }))
    const wrapper = await mountSection([invitation()])

    const renew = wrapper.findAll('button').find((button) => button.text().includes('Обновить'))
    await renew!.trigger('click')
    await flushPromises()

    expect(invitationsApi.renewInvitation).toHaveBeenCalledWith(1)
    expect(wrapper.find<HTMLInputElement>('.invitations__result input').element.value).toContain(
      '/invite/renewed',
    )
  })
})
