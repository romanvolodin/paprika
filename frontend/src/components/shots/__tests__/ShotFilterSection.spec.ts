import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShotFilterSection from '@/components/shots/ShotFilterSection.vue'

const options = [
  { value: 'none' as const, label: 'Не назначен' },
  { value: 11, label: 'Коля Зайцев' },
  { value: 12, label: 'Костя Соломонов' },
]

function mountSection(props: Partial<InstanceType<typeof ShotFilterSection>['$props']> = {}) {
  return mount(ShotFilterSection, {
    props: { title: 'Исполнитель', options, selected: [], inverted: false, ...props },
  })
}

function optionCheckboxes(wrapper: ReturnType<typeof mountSection>) {
  return wrapper.findAll('.filter-section__options .n-checkbox')
}

describe('ShotFilterSection', () => {
  it('shows the title and one checkbox per option', () => {
    const wrapper = mountSection()

    expect(wrapper.text()).toContain('Исполнитель')
    expect(wrapper.text()).toContain('Коля Зайцев')
    expect(optionCheckboxes(wrapper)).toHaveLength(3)
  })

  it('ticks the selected options', () => {
    const wrapper = mountSection({ selected: [11] })

    expect(optionCheckboxes(wrapper).map((box) => box.classes('n-checkbox--checked'))).toEqual([
      false,
      true,
      false,
    ])
  })

  it('emits the selection with a newly ticked option added', async () => {
    const wrapper = mountSection({ selected: [11] })

    await optionCheckboxes(wrapper)[2]!.trigger('click')

    expect(wrapper.emitted('change')).toEqual([[[11, 12], false]])
  })

  it('emits the selection without an option that was unticked', async () => {
    const wrapper = mountSection({ selected: ['none', 11] })

    await optionCheckboxes(wrapper)[1]!.trigger('click')

    expect(wrapper.emitted('change')).toEqual([[['none'], false]])
  })

  it('keeps the invert flag while options are ticked', async () => {
    const wrapper = mountSection({ selected: [11], inverted: true })

    await optionCheckboxes(wrapper)[2]!.trigger('click')

    expect(wrapper.emitted('change')).toEqual([[[11, 12], true]])
  })

  it('emits the invert flag with the selection unchanged', async () => {
    const wrapper = mountSection({ selected: [11] })

    await wrapper.find('.filter-section__invert').trigger('click')

    expect(wrapper.emitted('change')).toEqual([[[11], true]])
  })

  it('disables inverting while nothing is ticked', () => {
    const wrapper = mountSection()

    expect(wrapper.find('.filter-section__invert').classes()).toContain('n-checkbox--disabled')
  })

  it('shows "Сбросить" only when something is ticked, and it clears everything', async () => {
    expect(mountSection().text()).not.toContain('Сбросить')

    const wrapper = mountSection({ selected: [11], inverted: true })
    const reset = wrapper.findAll('button').find((button) => button.text() === 'Сбросить')
    await reset!.trigger('click')

    expect(wrapper.emitted('change')).toEqual([[[], false]])
  })

  it('draws coloured options as tags', () => {
    const wrapper = mountSection({
      title: 'Статус',
      options: [{ value: 3, label: 'Готов', color: '#00aa00' }],
    })

    expect(wrapper.find('.n-tag').text()).toBe('Готов')
  })
})
