import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ProjectSettingsView from '@/views/ProjectSettingsView.vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectPageStore } from '@/stores/projectPage'
import * as companiesApi from '@/api/companies'
import * as projectsApi from '@/api/projects'
import type { ProjectMemberOut } from '@/types/api'
import { buildProjectFor, roleRefOf, type StarterRole } from './starterRoles'

vi.mock('@/api/projects')
vi.mock('@/api/companies')

function buildMember(role: StarterRole): ProjectMemberOut {
  return {
    id: 1,
    user_id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    role: roleRefOf(role),
    created_at: '2026-01-01T00:00:00Z',
  }
}

const Host = defineComponent({
  setup() {
    return () =>
      h(NMessageProvider, null, {
        default: () => h(NDialogProvider, null, { default: () => h(ProjectSettingsView) }),
      })
  },
})

async function mountSettings(role: StarterRole) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects', name: 'project-list', component: { render: () => null } }],
  })

  const auth = useAuthStore()
  auth.currentUser = {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
  }
  const store = useProjectPageStore()
  store.project = buildProjectFor(role)
  store.members = [buildMember(role)]

  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('ProjectSettingsView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({ items: [] })
  })

  it.each(['admin', 'producer'] as const)('shows the delete button to a %s', async (role) => {
    const wrapper = await mountSettings(role)

    expect(wrapper.text()).toContain('Удалить проект')
  })

  it('hides the delete button from a coordinator, who can still change the settings', async () => {
    const wrapper = await mountSettings('coordinator')

    expect(wrapper.text()).not.toContain('Удалить проект')
    expect(wrapper.text()).not.toContain('У вас нет прав')
  })

  it.each(['executor', 'freelancer', 'client', 'readonly'] as const)(
    'shows only a no-access note to a %s who opens the address directly',
    async (role) => {
      const wrapper = await mountSettings(role)

      expect(wrapper.text()).toContain('У вас нет прав на настройки проекта')
      expect(wrapper.text()).not.toContain('Удалить проект')
      expect(projectsApi.deleteProject).not.toHaveBeenCalled()
    },
  )
})
