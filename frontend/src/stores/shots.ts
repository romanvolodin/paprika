import { ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type {
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  ShotCreateIn,
  ShotGroupOut,
  ShotOut,
  ShotStatusOut,
} from '@/types/api'

export type ShotListState = 'loading' | 'ready' | 'not-found' | 'error'

const MAX_PAGE_SIZE = 100

export const useShotsStore = defineStore('shots', () => {
  const state = ref<ShotListState>('loading')
  const project = ref<ProjectOut | null>(null)
  const members = ref<ProjectMemberOut[]>([])
  const statuses = ref<ShotStatusOut[]>([])
  const groups = ref<ShotGroupOut[]>([])
  const items = ref<ShotOut[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const search = ref('')
  const isLoading = ref(false)

  // `open` can be called again (e.g. navigating to another project)
  // while an earlier call is still in flight - only the latest one is
  // allowed to write its result.
  let openToken = 0

  async function fetchShots() {
    if (!project.value) return
    isLoading.value = true
    try {
      const result = await shotsApi.listShots(project.value.id, {
        page: page.value,
        page_size: pageSize.value,
        search: search.value || undefined,
      })
      items.value = result.items
      total.value = result.total
      page.value = result.page
      pageSize.value = result.page_size
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Resolve the project from its (company-unique) code and load
   * everything the shot list needs. The API only knows numeric ids, so
   * the code is looked up through the project list's exact `code`
   * filter.
   */
  async function open(company: CompanyOut, projectCode: string) {
    const token = ++openToken
    state.value = 'loading'
    project.value = null
    items.value = []
    total.value = 0
    page.value = 1
    search.value = ''

    try {
      const candidates = await projectsApi.listProjects(company.id, {
        code: projectCode,
        page_size: 1,
      })
      const found = candidates.items[0]
      if (token !== openToken) return
      if (!found) {
        state.value = 'not-found'
        return
      }

      const [statusList, groupList, memberList] = await Promise.all([
        shotsApi.listShotStatuses(company.id),
        shotsApi.listShotGroups(found.id, { page_size: MAX_PAGE_SIZE }),
        projectsApi.listProjectMembers(found.id),
      ])
      if (token !== openToken) return
      project.value = found
      statuses.value = statusList.items
      groups.value = groupList.items
      members.value = memberList.items

      await fetchShots()
      if (token !== openToken) return
      state.value = 'ready'
    } catch (error) {
      if (token !== openToken) return
      state.value = isAxiosError(error) && error.response?.status === 404 ? 'not-found' : 'error'
    }
  }

  async function setSearch(value: string) {
    search.value = value
    page.value = 1
    await fetchShots()
  }

  async function setPage(value: number) {
    page.value = value
    await fetchShots()
  }

  async function createShot(input: ShotCreateIn) {
    if (!project.value) return
    const created = await shotsApi.createShot(project.value.id, input)
    await fetchShots()
    return created
  }

  return {
    state,
    project,
    members,
    statuses,
    groups,
    items,
    total,
    page,
    pageSize,
    search,
    isLoading,
    open,
    setSearch,
    setPage,
    createShot,
  }
})
