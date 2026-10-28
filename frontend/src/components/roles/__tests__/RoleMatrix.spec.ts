import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RoleMatrix from '@/components/roles/RoleMatrix.vue'
import type { PermissionOut, RoleOut } from '@/types/api'

function buildRole(overrides: Partial<RoleOut>): RoleOut {
  return {
    id: 1,
    company_id: 1,
    name: 'Админ',
    color: '#00A64F',
    permissions: [],
    sees_all_projects: false,
    company_members_count: 0,
    project_members_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const catalog: PermissionOut[] = [
  {
    code: 'company.edit',
    label: 'Настройки компании',
    description: '',
    group: 'Компания',
    level: 'company',
  },
  {
    code: 'shot.create',
    label: 'Создание кадров',
    description: '',
    group: 'Кадры',
    level: 'project',
  },
  {
    code: 'shot.edit',
    label: 'Редактирование кадров',
    description: '',
    group: 'Кадры',
    level: 'project',
  },
]

const roles = [
  buildRole({
    id: 1,
    name: 'Админ',
    permissions: ['company.edit', 'shot.create'],
    sees_all_projects: true,
  }),
  buildRole({ id: 2, name: 'Клиент', permissions: [] }),
]

describe('RoleMatrix', () => {
  it('shows a column per role and a row per permission, under a heading per section', () => {
    const wrapper = mount(RoleMatrix, { props: { roles, catalog } })

    expect(wrapper.findAll('thead th').map((th) => th.text())).toEqual(['', 'Админ', 'Клиент'])
    expect(wrapper.findAll('.role-matrix__group').map((row) => row.text())).toEqual([
      'Компания',
      'Кадры',
    ])
    expect(wrapper.text()).toContain('Создание кадров')
    expect(wrapper.text()).toContain('Редактирование кадров')
  })

  it('marks what each role has', () => {
    const wrapper = mount(RoleMatrix, { props: { roles, catalog } })

    const row = wrapper.findAll('tbody tr').find((tr) => tr.text().includes('Создание кадров'))
    expect(row?.findAll('td').map((td) => td.text())).toEqual(['✓', '—'])
    const edit = wrapper.findAll('tbody tr').find((tr) => tr.text().includes('Редактирование'))
    expect(edit?.findAll('td').map((td) => td.text())).toEqual(['—', '—'])
  })

  it('shows which roles see all projects', () => {
    const wrapper = mount(RoleMatrix, { props: { roles, catalog } })

    const row = wrapper.find('.role-matrix__scope-row')
    expect(row.text()).toContain('Видит все проекты компании')
    expect(row.findAll('td').map((td) => td.text())).toEqual(['✓', '—'])
  })

  it('tells which role was picked when its name is clicked', async () => {
    const wrapper = mount(RoleMatrix, { props: { roles, catalog } })

    await wrapper.findAll('.role-matrix__role')[1]!.trigger('click')

    expect(wrapper.emitted('select')).toEqual([[2]])
  })
})
