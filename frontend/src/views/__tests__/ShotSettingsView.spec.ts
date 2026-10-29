import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import { createMemoryHistory, createRouter } from 'vue-router'
import ShotSettingsView from '@/views/ShotSettingsView.vue'
import { useShotDetailStore } from '@/stores/shotDetail'
import * as shotsApi from '@/api/shots'
import type { ShotOut } from '@/types/api'
import { buildProjectFor, roleRefOf, type StarterRole } from './starterRoles'

vi.mock('@/api/shots')

const shot: ShotOut = {
  id: 5,
  project_id: 1,
  group_ids: [3],
  status_id: 1,
  name: '0010',
  rec_timecode: 100,
  duration: 48,
  created_by: null,
  updated_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function mountSettings(role: StarterRole) {
  const store = useShotDetailStore()
  store.project = buildProjectFor(role)
  store.shot = shot
  store.groups = [
    {
      id: 3,
      project_id: 1,
      name: 'Эпизод 1',
      created_by: null,
      updated_by: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ]
  store.members = [
    {
      id: 1,
      user_id: 1,
      email: 'a@paprika.dev',
      first_name: 'A',
      last_name: 'One',
      role: roleRefOf(role),
      created_at: '2026-01-01T00:00:00Z',
    },
  ]
  // The permissions composable looks the current user up by id.
  return mountWithProviders()
}

async function mountWithProviders() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }],
  })
  const Host = defineComponent({
    render: () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () => h(ShotSettingsView, { companySlug: 'acme', projectCode: 'PRJ' }),
          }),
      }),
  })
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('ShotSettingsView', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    const { useAuthStore } = await import('@/stores/auth')
    useAuthStore().currentUser = {
      id: 1,
      email: 'a@paprika.dev',
      first_name: 'A',
      last_name: 'One',
      avatar: null,
      is_active: true,
      date_joined: '2026-01-01T00:00:00Z',
      is_superuser: false,
      must_change_password: false,
    }
  })

  it('shows the shot name as a disabled field and the current values', async () => {
    const wrapper = await mountSettings('coordinator')

    const inputs = wrapper.findAll('input')
    expect((inputs[0].element as HTMLInputElement).value).toBe('0010')
    expect(inputs[0].attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Эпизод 1')
  })

  it('saves groups and timings without touching the status', async () => {
    vi.mocked(shotsApi.updateShot).mockResolvedValue(shot)
    const wrapper = await mountSettings('coordinator')

    const save = wrapper.findAll('button').find((button) => button.text() === 'Сохранить')
    await save!.trigger('click')
    await flushPromises()

    expect(shotsApi.updateShot).toHaveBeenCalledWith(5, {
      group_ids: [3],
      rec_timecode: 100,
      duration: 48,
    })
  })

  it('shows the save button and the delete zone to a member who can write', async () => {
    const wrapper = await mountSettings('coordinator')

    const buttons = wrapper.findAll('button').map((button) => button.text())
    expect(buttons).toContain('Сохранить')
    expect(buttons).toContain('Удалить кадр')
  })

  it('shows the fields read-only to a client, without save or delete', async () => {
    const wrapper = await mountSettings('readonly')

    const buttons = wrapper.findAll('button').map((button) => button.text())
    expect(buttons).not.toContain('Сохранить')
    expect(buttons).not.toContain('Удалить кадр')
    expect(wrapper.text()).toContain('Эпизод 1')
  })
})
