import { apiClient } from './client'
import type {
  ShotGroupListOut,
  ShotGroupListQuery,
  ShotListOut,
  ShotListQuery,
  ShotStatusListOut,
} from '@/types/api'

export function listShots(projectId: number, query: ShotListQuery = {}) {
  return apiClient
    .get<ShotListOut>(`/projects/${projectId}/shots/`, { params: query })
    .then((res) => res.data)
}

export function listShotGroups(projectId: number, query: ShotGroupListQuery = {}) {
  return apiClient
    .get<ShotGroupListOut>(`/projects/${projectId}/shot-groups/`, { params: query })
    .then((res) => res.data)
}

export function listShotStatuses(companyId: number) {
  return apiClient
    .get<ShotStatusListOut>(`/companies/${companyId}/shot-statuses/`)
    .then((res) => res.data)
}
