import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AddMemberForm from '@/components/company/AddMemberForm.vue'
import type { RoleOut } from '@/types/api'

const roles = [
  { id: 4, name: 'Исполнитель', color: '#E971B8' },
  { id: 5, name: 'Клиент', color: '#8A8A8A' },
] as RoleOut[]

function mountForm() {
  return mount(AddMemberForm, { props: { roles, isSubmitting: false } })
}

async function fill(wrapper: ReturnType<typeof mountForm>) {
  const inputs = wrapper.findAll('input')
  await inputs[0]!.setValue('  new@paprika.dev ')
  await inputs[1]!.setValue('Анна')
  await inputs[2]!.setValue('Иванова')
  await inputs[3]!.setValue('temporary-pass-1')
}

describe('AddMemberForm', () => {
  it('cannot be submitted while something is missing', async () => {
    const wrapper = mountForm()
    await fill(wrapper)

    const submit = wrapper.find('button[type="submit"]')

    // No role chosen yet.
    expect(submit.attributes('disabled')).toBeDefined()
  })

  it('generates a temporary password', async () => {
    const wrapper = mountForm()

    const generate = wrapper.findAll('button').find((b) => b.text().includes('Сгенерировать'))
    await generate!.trigger('click')

    const password = wrapper.findAll('input')[3]!.element.value
    expect(password).toHaveLength(14)
  })

  it('sends what was typed, trimmed, with the chosen role', async () => {
    const wrapper = mountForm()
    await fill(wrapper)
    wrapper.findComponent({ name: 'Select' }).vm.$emit('update:value', 4)
    await wrapper.vm.$nextTick()

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')).toEqual([
      [
        {
          email: 'new@paprika.dev',
          first_name: 'Анна',
          last_name: 'Иванова',
          password: 'temporary-pass-1',
          role_id: 4,
        },
      ],
    ])
  })

  it('starts over after reset()', async () => {
    const wrapper = mountForm()
    await fill(wrapper)

    ;(wrapper.vm as unknown as { reset: () => void }).reset()
    await wrapper.vm.$nextTick()

    expect(
      wrapper
        .findAll('input')
        .map((input) => input.element.value)
        .slice(0, 4),
    ).toEqual(['', '', '', ''])
  })
})
