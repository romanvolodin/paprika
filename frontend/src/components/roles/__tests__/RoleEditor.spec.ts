import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RoleEditor from '@/components/roles/RoleEditor.vue'
import type { PermissionOut, RoleOut } from '@/types/api'

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

const role: RoleOut = {
  id: 3,
  company_id: 1,
  name: 'Координатор',
  color: '#0A84DB',
  permissions: ['shot.create'],
  sees_all_projects: false,
  company_members_count: 2,
  project_members_count: 5,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function mountEditor(props: Partial<InstanceType<typeof RoleEditor>['$props']> = {}) {
  return mount(RoleEditor, {
    props: { role, catalog, canEdit: true, isSaving: false, ...props },
  })
}

describe('RoleEditor', () => {
  it('shows the role with its permissions ticked', () => {
    const wrapper = mountEditor()

    expect(wrapper.text()).toContain('Координатор')
    const checked = wrapper.findAll('.n-checkbox').map((box) => box.classes('n-checkbox--checked'))
    expect(checked).toEqual([false, true])
  })

  it('groups the permissions by section and says where each section applies', () => {
    const wrapper = mountEditor()

    const titles = wrapper.findAll('.role-editor__group-title').map((title) => title.text())
    expect(titles).toEqual(['Компания', 'Кадры'])
    expect(wrapper.text()).toContain('Действуют по роли человека в компании')
    expect(wrapper.text()).toContain('Действуют по роли человека в проекте')
  })

  it('sends what was changed when saved', async () => {
    const wrapper = mountEditor()

    await wrapper.find('.role-editor__name input').setValue('Старший координатор')
    await wrapper.findAll('.n-checkbox')[0]!.trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('save')).toEqual([
      [
        {
          name: 'Старший координатор',
          color: '#0A84DB',
          permissions: ['shot.create', 'company.edit'],
          sees_all_projects: false,
        },
      ],
    ])
  })

  it('does not send a role without a name', async () => {
    const wrapper = mountEditor()

    await wrapper.find('.role-editor__name input').setValue('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('starts empty for a new role', () => {
    const wrapper = mountEditor({ role: null })

    expect(wrapper.text()).toContain('Новая роль')
    expect(wrapper.text()).toContain('Создать роль')
    expect(wrapper.findAll('.n-checkbox--checked')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Удалить')
  })

  it('asks to delete the role', async () => {
    const wrapper = mountEditor()

    const button = wrapper.findAll('button').find((candidate) => candidate.text() === 'Удалить')
    await button!.trigger('click')

    expect(wrapper.emitted('remove')).toHaveLength(1)
  })

  it('offers no way to save or delete without the right to edit', () => {
    const wrapper = mountEditor({ canEdit: false })

    expect(wrapper.text()).not.toContain('Сохранить')
    expect(wrapper.text()).not.toContain('Удалить')
  })

  it('switches to another role when it is replaced', async () => {
    const wrapper = mountEditor()

    await wrapper.setProps({ role: { ...role, id: 4, name: 'Клиент', permissions: [] } })

    expect(wrapper.text()).toContain('Клиент')
    expect(wrapper.findAll('.n-checkbox--checked')).toHaveLength(0)
  })
})
