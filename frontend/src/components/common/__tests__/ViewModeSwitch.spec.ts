import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ViewModeSwitch from '@/components/common/ViewModeSwitch.vue'

describe('ViewModeSwitch', () => {
  it('marks only the current mode as pressed', () => {
    const wrapper = mount(ViewModeSwitch, { props: { modelValue: 'cards' } })

    expect(wrapper.get('button[aria-label="Карточки"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button[aria-label="Таблица"]').attributes('aria-pressed')).toBe('false')
  })

  it('emits the chosen mode', async () => {
    const wrapper = mount(ViewModeSwitch, { props: { modelValue: 'table' } })

    await wrapper.get('button[aria-label="Карточки"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')).toEqual([['cards']])
  })
})
