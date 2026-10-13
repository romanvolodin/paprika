import { apiClient } from './client'
import type {
  ShotCreateIn,
  ShotGroupListOut,
  ShotGroupListQuery,
  ShotListOut,
  ShotListQuery,
  ShotOut,
  ShotStatusListOut,
  ShotUpdateIn,
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

export function createShot(projectId: number, input: ShotCreateIn) {
  return apiClient.post<ShotOut>(`/projects/${projectId}/shots/`, input).then((res) => res.data)
}

export function updateShot(shotId: number, input: ShotUpdateIn) {
  return apiClient.patch<ShotOut>(`/shots/${shotId}/`, input).then((res) => res.data)
}

export function deleteShot(shotId: number) {
  return apiClient.delete<void>(`/shots/${shotId}/`)
}
