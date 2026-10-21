import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import UserAvatar from '@/components/common/UserAvatar.vue'

const anna = {
  first_name: 'Анна',
  last_name: 'Смирнова',
  email: 'anna@example.com',
  avatar: null,
}

describe('UserAvatar', () => {
  it('shows the picture when the user has one', () => {
    const wrapper = mount(UserAvatar, {
      props: { user: { ...anna, avatar: 'http://localhost/media/anna.png' } },
    })

    expect(wrapper.find('img').attributes('src')).toBe('http://localhost/media/anna.png')
  })

  it('shows the initials of a user without a picture', () => {
    const wrapper = mount(UserAvatar, { props: { user: anna } })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toBe('АС')
  })

  it('falls back to the first letter of the e-mail for a user without a name', () => {
    const wrapper = mount(UserAvatar, {
      props: { user: { ...anna, first_name: '', last_name: '' } },
    })

    expect(wrapper.text()).toBe('A')
  })

  it('shows a question mark for a deleted user', () => {
    const wrapper = mount(UserAvatar, { props: { user: null } })

    expect(wrapper.text()).toBe('?')
  })
})
