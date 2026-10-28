import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import CompanyRolesView from '@/views/CompanyRolesView.vue'
import * as companiesApi from '@/api/companies'
import * as rolesApi from '@/api/roles'
import type { CompanyOut, PermissionOut, RoleOut } from '@/types/api'

vi.mock('@/api/companies')
vi.mock('@/api/roles')

function buildCompany(myPermissions: string[]): CompanyOut {
  return {
    id: 7,
    name: 'Acme',
    slug: 'acme',
    my_permissions: myPermissions,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function buildRole(overrides: Partial<RoleOut>): RoleOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Админ',
    color: '#00A64F',
    permissions: ['company.edit'],
    sees_all_projects: true,
    company_members_count: 1,
    project_members_count: 2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const catalog: PermissionOut[] = [
  {
    code: 'company.edit',
    label: 'Настройки компании',
    description: 'Менять название',
    group: 'Компания',
    level: 'company',
  },
  {
    code: 'shot.create',
    label: 'Создание кадров',
    description: 'Добавлять кадры',
    group: 'Кадры',
    level: 'project',
  },
]

const roles = [
  buildRole({ id: 1, name: 'Админ' }),
  buildRole({
    id: 2,
    name: 'Клиент',
    color: '#8A8A8A',
    permissions: [],
    sees_all_projects: false,
    company_members_count: 0,
    project_members_count: 0,
  }),
]

const Host = defineComponent({
  setup() {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, { default: () => h(CompanyRolesView, { companyId: 7 }) }),
      })
  },
})

async function mountRoles(myPermissions: string[]) {
  vi.mocked(companiesApi.getCompany).mockResolvedValue(buildCompany(myPermissions))
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/companies/:id', name: 'company-detail', component: { render: () => null } }],
  })
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll('button').find((button) => button.text().includes(text))
}

describe('CompanyRolesView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({ items: [] })
    vi.mocked(rolesApi.listCompanyRoles).mockResolvedValue({ items: roles })
    vi.mocked(rolesApi.listPermissions).mockResolvedValue({ items: catalog })
  })

  it('lists the roles with how many people have them', async () => {
    const { wrapper } = await mountRoles(['company.roles'])

    const items = wrapper.findAll('.company-roles__item').map((item) => item.text())
    expect(items[0]).toContain('Админ')
    expect(items[0]).toContain('1 в компании · 2 в проектах')
    expect(items[1]).toContain('Клиент')
  })

  it('opens the first role in the editor', async () => {
    const { wrapper } = await mountRoles(['company.roles'])

    expect(wrapper.find('.role-editor__title').text()).toBe('Админ')
    expect(wrapper.text()).toContain('Настройки компании')
  })

  it('shows another role when it is picked', async () => {
    const { wrapper } = await mountRoles(['company.roles'])

    await wrapper.findAll('.company-roles__item')[1]!.trigger('click')

    expect(wrapper.find('.role-editor__title').text()).toBe('Клиент')
  })

  it('saves the changes to a role', async () => {
    vi.mocked(rolesApi.updateRole).mockResolvedValue(roles[0]!)
    const { wrapper } = await mountRoles(['company.roles'])

    await wrapper.find('.role-editor__name input').setValue('Владелец')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(rolesApi.updateRole).toHaveBeenCalledWith(1, {
      name: 'Владелец',
      color: '#00A64F',
      permissions: ['company.edit'],
      sees_all_projects: true,
    })
    expect(rolesApi.listCompanyRoles).toHaveBeenCalledTimes(2)
  })

  it('creates a role and opens it', async () => {
    const created = buildRole({ id: 9, name: 'Монтажёр', permissions: [] })
    vi.mocked(rolesApi.createRole).mockResolvedValue(created)
    vi.mocked(rolesApi.listCompanyRoles)
      .mockResolvedValueOnce({ items: roles })
      .mockResolvedValue({ items: [...roles, created] })
    const { wrapper } = await mountRoles(['company.roles'])

    await buttonByText(wrapper, 'Новая роль')!.trigger('click')
    expect(wrapper.find('.role-editor__title').text()).toBe('Новая роль')
    await wrapper.find('.role-editor__name input').setValue('Монтажёр')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(rolesApi.createRole).toHaveBeenCalledWith(7, {
      name: 'Монтажёр',
      color: '#888888',
      permissions: [],
      sees_all_projects: false,
    })
    expect(wrapper.find('.role-editor__title').text()).toBe('Монтажёр')
  })

  it('shows the matrix of roles and permissions', async () => {
    const { wrapper } = await mountRoles(['company.roles'])

    await buttonByText(wrapper, 'Матрица')!.trigger('click')

    expect(wrapper.find('.role-matrix').exists()).toBe(true)
    expect(wrapper.find('.role-editor').exists()).toBe(false)
  })

  it('goes back to the list with the role whose name was clicked in the matrix', async () => {
    const { wrapper } = await mountRoles(['company.roles'])
    await buttonByText(wrapper, 'Матрица')!.trigger('click')

    await wrapper.findAll('.role-matrix__role')[1]!.trigger('click')

    expect(wrapper.find('.role-matrix').exists()).toBe(false)
    expect(wrapper.find('.role-editor__title').text()).toBe('Клиент')
  })

  it('lets someone without the permission look but not change', async () => {
    const { wrapper } = await mountRoles([])

    expect(wrapper.text()).toContain('Менять роли могут только те, у кого есть разрешение')
    expect(buttonByText(wrapper, 'Новая роль')).toBeUndefined()
    expect(buttonByText(wrapper, 'Сохранить')).toBeUndefined()
    expect(wrapper.find('.role-editor__title').text()).toBe('Админ')
  })

  it('takes you back to the company', async () => {
    const { wrapper, router } = await mountRoles(['company.roles'])

    await buttonByText(wrapper, 'К компании')!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('company-detail')
    expect(router.currentRoute.value.params.id).toBe('7')
  })
})
