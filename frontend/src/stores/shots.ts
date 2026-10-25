import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import { usePageSize } from '@/composables/usePageSize'
import type {
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  ShotCreateIn,
  ShotFiltersOut,
  ShotGroupOut,
  ShotOut,
  ShotStatusOut,
} from '@/types/api'

export type ShotListState = 'loading' | 'ready' | 'not-found' | 'error'

/** A user id, or `'none'` for tasks that have no assignee. */
export type AssigneeFilterValue = number | 'none'

export interface AssigneeFilterOption {
  value: AssigneeFilterValue
  label: string
}

const MAX_PAGE_SIZE = 100

function memberName(member: ProjectMemberOut): string {
  return `${member.first_name} ${member.last_name}`.trim() || member.email
}

/**
 * The values to send for a filter: the ticked ones, or - with
 * "invert" - every other available one. `null` means "no filter".
 */
function effectiveValues<T>(available: T[], selected: T[], inverted: boolean): T[] | null {
  if (selected.length === 0) return null
  return inverted ? available.filter((value) => !selected.includes(value)) : selected
}

export const useShotsStore = defineStore('shots', () => {
  const state = ref<ShotListState>('loading')
  const project = ref<ProjectOut | null>(null)
  const members = ref<ProjectMemberOut[]>([])
  const statuses = ref<ShotStatusOut[]>([])
  const groups = ref<ShotGroupOut[]>([])
  const items = ref<ShotOut[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = usePageSize('shots')
  const search = ref('')
  const isLoading = ref(false)

  const filterOptions = ref<ShotFiltersOut | null>(null)
  const statusSelected = ref<number[]>([])
  const statusInverted = ref(false)
  const assigneeSelected = ref<AssigneeFilterValue[]>([])
  const assigneeInverted = ref(false)

  // Only the statuses that at least one shot has, in the company's order.
  const statusOptions = computed(() => {
    const used = filterOptions.value?.status_ids ?? []
    return statuses.value.filter((status) => used.includes(status.id))
  })

  const assigneeOptions = computed<AssigneeFilterOption[]>(() => {
    const filters = filterOptions.value
    if (!filters) return []
    const options: AssigneeFilterOption[] = []
    if (filters.has_unassigned) options.push({ value: 'none', label: 'Не назначен' })
    const named = members.value
      .filter((member) => filters.assignee_ids.includes(member.user_id))
      .map((member) => ({ value: member.user_id, label: memberName(member) }))
      .sort((a, b) => a.label.localeCompare(b.label, 'ru'))
    return [...options, ...named]
  })

  // `open` can be called again (e.g. navigating to another project)
  // while an earlier call is still in flight - only the latest one is
  // allowed to write its result.
  let openToken = 0
  // Same for the list itself: filters can change faster than the
  // server answers.
  let fetchToken = 0

  async function fetchShots() {
    if (!project.value) return
    const token = ++fetchToken

    const statusIds = effectiveValues(
      statusOptions.value.map((status) => status.id),
      statusSelected.value,
      statusInverted.value,
    )
    const assignees = effectiveValues(
      assigneeOptions.value.map((option) => option.value),
      assigneeSelected.value,
      assigneeInverted.value,
    )

    // Everything ticked and then inverted leaves nothing to show.
    if (statusIds?.length === 0 || assignees?.length === 0) {
      items.value = []
      total.value = 0
      return
    }

    isLoading.value = true
    try {
      const result = await shotsApi.listShots(project.value.id, {
        page: page.value,
        page_size: pageSize.value,
        search: search.value || undefined,
        status: statusIds?.join(','),
        assigned_to: assignees?.join(','),
      })
      if (token !== fetchToken) return
      items.value = result.items
      total.value = result.total
      page.value = result.page
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  function applyFilterOptions(options: ShotFiltersOut) {
    filterOptions.value = options
    // A ticked value that no shot has any more would filter by
    // something the panel no longer shows.
    statusSelected.value = statusSelected.value.filter((id) => options.status_ids.includes(id))
    assigneeSelected.value = assigneeSelected.value.filter((value) =>
      value === 'none' ? options.has_unassigned : options.assignee_ids.includes(value),
    )
    if (statusSelected.value.length === 0) statusInverted.value = false
    if (assigneeSelected.value.length === 0) assigneeInverted.value = false
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
    filterOptions.value = null
    statusSelected.value = []
    statusInverted.value = false
    assigneeSelected.value = []
    assigneeInverted.value = false

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

      const [statusList, groupList, memberList, filters] = await Promise.all([
        shotsApi.listShotStatuses(company.id),
        shotsApi.listShotGroups(found.id, { page_size: MAX_PAGE_SIZE }),
        projectsApi.listProjectMembers(found.id),
        shotsApi.getShotFilters(found.id),
      ])
      if (token !== openToken) return
      project.value = found
      statuses.value = statusList.items
      groups.value = groupList.items
      members.value = memberList.items
      filterOptions.value = filters

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

  async function setPageSize(value: number) {
    pageSize.value = value
    page.value = 1
    await fetchShots()
  }

  async function setStatusFilter(selected: number[], inverted: boolean) {
    statusSelected.value = selected
    statusInverted.value = selected.length > 0 && inverted
    page.value = 1
    await fetchShots()
  }

  async function setAssigneeFilter(selected: AssigneeFilterValue[], inverted: boolean) {
    assigneeSelected.value = selected
    assigneeInverted.value = selected.length > 0 && inverted
    page.value = 1
    await fetchShots()
  }

  async function createShot(input: ShotCreateIn) {
    if (!project.value) return
    const created = await shotsApi.createShot(project.value.id, input)
    // A new shot can bring a status the panel did not offer yet.
    await shotsApi
      .getShotFilters(project.value.id)
      .then(applyFilterOptions)
      .catch(() => undefined)
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
    statusOptions,
    assigneeOptions,
    statusSelected,
    statusInverted,
    assigneeSelected,
    assigneeInverted,
    open,
    setSearch,
    setPage,
    setPageSize,
    setStatusFilter,
    setAssigneeFilter,
    createShot,
  }
})
