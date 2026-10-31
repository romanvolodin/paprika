import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { NSelect } from 'naive-ui'
import ProjectInviteForm from '@/components/projects/ProjectInviteForm.vue'
import type { RoleOut } from '@/types/api'

function role(id: number, name: string, permissions: string[], sees = false): RoleOut {
  return {
    id,
    company_id: 1,
    name,
    color: '#888888',
    permissions,
    sees_all_projects: sees,
    company_members_count: 0,
    project_members_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const roles = [
  role(1, 'Админ', ['company.delete', 'shot.create'], true),
  role(2, 'Продюсер', ['company.members', 'shot.create'], true),
  role(3, 'Координатор', ['shot.create']),
  role(4, 'Клиент', ['chat.write']),
  role(5, 'Свой широкий', [], true),
]

function mountForm() {
  return mount(ProjectInviteForm, { props: { roles, isSubmitting: false } })
}

describe('ProjectInviteForm', () => {
  it('offers only the roles without company rights that see just their own projects', () => {
    const wrapper = mountForm()

    const options = wrapper.findComponent(NSelect).props('options') as { label: string }[]
    expect(options.map((option) => option.label)).toEqual(['Координатор', 'Клиент'])
  })

  it('cannot be sent without an email and a role', async () => {
    const wrapper = mountForm()
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()

    await wrapper.find('input').setValue('new@paprika.dev')

    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('sends the trimmed email and the chosen role', async () => {
    const wrapper = mountForm()
    await wrapper.find('input').setValue('  new@paprika.dev ')
    wrapper.findComponent(NSelect).vm.$emit('update:value', 4)
    await wrapper.vm.$nextTick()

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')).toEqual([[{ email: 'new@paprika.dev', role_id: 4 }]])
  })

  it('starts over after reset()', async () => {
    const wrapper = mountForm()
    await wrapper.find('input').setValue('new@paprika.dev')

    ;(wrapper.vm as unknown as { reset: () => void }).reset()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('input').element.value).toBe('')
  })
})
