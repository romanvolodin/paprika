import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { NMessageProvider } from 'naive-ui'
import InvitationLink from '@/components/company/InvitationLink.vue'

const Host = defineComponent({
  setup() {
    return () => h(NMessageProvider, null, { default: () => h(InvitationLink, { token: 'tok-1' }) })
  },
})

describe('InvitationLink', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the whole link to pass on', () => {
    const wrapper = mount(Host)

    expect(wrapper.find('input').element.value).toBe(`${window.location.origin}/invite/tok-1`)
  })

  it('copies it', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })
    const wrapper = mount(Host)

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/invite/tok-1`)
  })
})
