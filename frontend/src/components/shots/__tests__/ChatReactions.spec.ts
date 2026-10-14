import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ChatReactions from '@/components/shots/ChatReactions.vue'
import type { ReactionSummaryOut } from '@/types/api'

const reactions: ReactionSummaryOut[] = [
  { emoji: '👍', user_ids: [1, 2, 3] },
  { emoji: '🔥', user_ids: [2] },
]

let wrapper: VueWrapper | null = null

function mountReactions(props: {
  reactions?: ReactionSummaryOut[]
  canReact?: boolean
  currentUserId?: number | null
}) {
  wrapper = mount(ChatReactions, {
    props: { reactions, currentUserId: 1, canReact: true, ...props },
    attachTo: document.body,
  })
  return wrapper
}

describe('ChatReactions', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  it('shows each emoji with the number of people who used it', () => {
    const chips = mountReactions({}).findAll('.chat-reactions__chip')

    expect(chips.map((chip) => chip.text())).toEqual(['👍3', '🔥1'])
  })

  it('highlights the emoji the current user has put', () => {
    const chips = mountReactions({ currentUserId: 1 }).findAll('.chat-reactions__chip')

    expect(chips[0]?.classes()).toContain('chat-reactions__chip--mine')
    expect(chips[1]?.classes()).not.toContain('chat-reactions__chip--mine')
  })

  it('highlights nothing when the current user is unknown', () => {
    const chips = mountReactions({ currentUserId: null }).findAll('.chat-reactions__chip--mine')

    expect(chips).toHaveLength(0)
  })

  it('asks to toggle an emoji when its chip is clicked', async () => {
    const view = mountReactions({})

    await view.findAll('.chat-reactions__chip')[1]?.trigger('click')

    expect(view.emitted('toggle')).toEqual([['🔥']])
  })

  it('offers a palette and toggles the chosen emoji', async () => {
    const view = mountReactions({})

    await view.find('.chat-reactions__add').trigger('click')
    await flushPromises()
    const pick = [...document.body.querySelectorAll<HTMLElement>('.chat-reactions__pick')].find(
      (button) => button.textContent?.trim() === '🎉',
    )
    expect(pick).toBeDefined()
    pick?.click()
    await flushPromises()

    expect(view.emitted('toggle')).toEqual([['🎉']])
  })

  it('shows the chips but no controls to someone who cannot react', () => {
    const view = mountReactions({ canReact: false })

    const chips = view.findAll('.chat-reactions__chip')
    expect(chips).toHaveLength(2)
    expect(chips.every((chip) => chip.attributes('disabled') !== undefined)).toBe(true)
    expect(view.find('.chat-reactions__add').exists()).toBe(false)
  })

  it('renders nothing for a message without reactions that cannot be reacted to', () => {
    const view = mountReactions({ reactions: [], canReact: false })

    expect(view.find('.chat-reactions').exists()).toBe(false)
  })

  it('still offers the add button on a message without reactions', () => {
    const view = mountReactions({ reactions: [], canReact: true })

    expect(view.find('.chat-reactions__add').exists()).toBe(true)
  })
})
