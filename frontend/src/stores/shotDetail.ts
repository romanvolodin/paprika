import { ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type {
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  ShotGroupOut,
  ShotOut,
  ShotStatusOut,
  ShotUpdateIn,
} from '@/types/api'

export type ShotDetailState = 'loading' | 'ready' | 'not-found' | 'error'

const MAX_PAGE_SIZE = 100

export const useShotDetailStore = defineStore('shotDetail', () => {
  const state = ref<ShotDetailState>('loading')
  const project = ref<ProjectOut | null>(null)
  const shot = ref<ShotOut | null>(null)
  const members = ref<ProjectMemberOut[]>([])
  const statuses = ref<ShotStatusOut[]>([])
  const groups = ref<ShotGroupOut[]>([])

  // A newer `open` call invalidates any earlier one still in flight.
  let openToken = 0

  /**
   * Resolve the project (by its company-unique code) and the shot (by
   * its project-unique name) from their URL form, using the exact
   * `code` / `name` list filters, then load what the page displays.
   */
  async function open(company: CompanyOut, projectCode: string, shotName: string) {
    const token = ++openToken
    state.value = 'loading'
    project.value = null
    shot.value = null

    try {
      const projects = await projectsApi.listProjects(company.id, {
        code: projectCode,
        page_size: 1,
      })
      const foundProject = projects.items[0]
      if (token !== openToken) return
      if (!foundProject) {
        state.value = 'not-found'
        return
      }

      const [shotList, statusList, groupList, memberList] = await Promise.all([
        shotsApi.listShots(foundProject.id, { name: shotName, page_size: 1 }),
        shotsApi.listShotStatuses(company.id),
        shotsApi.listShotGroups(foundProject.id, { page_size: MAX_PAGE_SIZE }),
        projectsApi.listProjectMembers(foundProject.id),
      ])
      if (token !== openToken) return
      const foundShot = shotList.items[0]
      if (!foundShot) {
        state.value = 'not-found'
        return
      }

      project.value = foundProject
      shot.value = foundShot
      statuses.value = statusList.items
      groups.value = groupList.items
      members.value = memberList.items
      state.value = 'ready'
    } catch (error) {
      if (token !== openToken) return
      state.value = isAxiosError(error) && error.response?.status === 404 ? 'not-found' : 'error'
    }
  }

  async function updateShot(input: ShotUpdateIn) {
    if (!shot.value) return
    shot.value = await shotsApi.updateShot(shot.value.id, input)
  }

  async function deleteShot() {
    if (!shot.value) return
    await shotsApi.deleteShot(shot.value.id)
  }

  return { state, project, shot, members, statuses, groups, open, updateShot, deleteShot }
})
