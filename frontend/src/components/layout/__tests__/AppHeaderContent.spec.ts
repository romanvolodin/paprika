import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import AppHeaderContent from '@/components/layout/AppHeaderContent.vue'
import { appHeaderSlot, setAppHeaderSlot } from '@/composables/useAppHeaderSlot'

const open = ref(true)

const Page = defineComponent({
  render: () =>
    h('div', { 'data-test': 'page' }, [
      open.value
        ? h(AppHeaderContent, null, { default: () => h('span', { 'data-test': 'bar' }, 'bar') })
        : null,
    ]),
})

describe('AppHeaderContent', () => {
  afterEach(() => {
    setAppHeaderSlot(null)
    open.value = true
  })

  it('renders in place when the app header has no slot', () => {
    const wrapper = mount(Page)

    expect(wrapper.find('[data-test="page"] [data-test="bar"]').exists()).toBe(true)
  })

  it('moves its content into the app header slot and removes it with the page', async () => {
    const target = document.createElement('div')
    document.body.appendChild(target)
    const wrapper = mount(Page, { attachTo: document.body })

    setAppHeaderSlot(target)
    await nextTick()

    expect(appHeaderSlot.value).toBe(target)
    expect(target.querySelector('[data-test="bar"]')).not.toBeNull()
    expect(wrapper.find('[data-test="page"] [data-test="bar"]').exists()).toBe(false)

    open.value = false
    await nextTick()
    expect(target.querySelector('[data-test="bar"]')).toBeNull()

    wrapper.unmount()
    target.remove()
  })
})
