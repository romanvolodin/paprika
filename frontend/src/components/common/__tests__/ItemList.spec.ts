import { describe, expect, it } from 'vitest'
import { h } from 'vue'
import { mount } from '@vue/test-utils'
import ItemList from '@/components/common/ItemList.vue'

interface Row {
  id: number
  name: string
}

const items: Row[] = [
  { id: 1, name: 'First' },
  { id: 2, name: 'Second' },
]

function mountList(props: { mode: 'table' | 'cards'; items?: Row[]; loading?: boolean }) {
  return mount(ItemList<Row>, {
    props: {
      items,
      columns: [{ title: 'Имя', key: 'name' }],
      rowKey: (row: Row) => row.id,
      ...props,
    },
    slots: {
      card: ({ item }: { item: Row }) => h('div', { class: 'test-card' }, item.name),
    },
  })
}

describe('ItemList', () => {
  it('renders a table with the columns in table mode', () => {
    const wrapper = mountList({ mode: 'table' })

    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.text()).toContain('First')
    expect(wrapper.text()).toContain('Second')
    expect(wrapper.findAll('.test-card')).toHaveLength(0)
  })

  it('renders one card per item through the card slot in cards mode', () => {
    const wrapper = mountList({ mode: 'cards' })

    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.findAll('.test-card').map((card) => card.text())).toEqual(['First', 'Second'])
  })

  it('says nothing was found when there are no items, in both modes', () => {
    expect(mountList({ mode: 'cards', items: [] }).text()).toContain('Ничего не найдено')
    expect(mountList({ mode: 'table', items: [] }).text()).toContain('Ничего не найдено')
  })

  it('does not say nothing was found while loading in cards mode', () => {
    const wrapper = mountList({ mode: 'cards', items: [], loading: true })

    expect(wrapper.text()).not.toContain('Ничего не найдено')
  })
})
