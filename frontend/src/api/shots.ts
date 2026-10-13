import { apiClient } from './client'
import type {
  ShotCreateIn,
  ShotGroupCreateIn,
  ShotGroupListOut,
  ShotGroupListQuery,
  ShotGroupOut,
  ShotGroupUpdateIn,
  ShotListOut,
  ShotListQuery,
  ShotOut,
  ShotStatusCreateIn,
  ShotStatusListOut,
  ShotStatusOut,
  ShotStatusUpdateIn,
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

export function createShotGroup(projectId: number, input: ShotGroupCreateIn) {
  return apiClient
    .post<ShotGroupOut>(`/projects/${projectId}/shot-groups/`, input)
    .then((res) => res.data)
}

export function renameShotGroup(groupId: number, input: ShotGroupUpdateIn) {
  return apiClient.patch<ShotGroupOut>(`/shot-groups/${groupId}/`, input).then((res) => res.data)
}

export function deleteShotGroup(groupId: number) {
  return apiClient.delete<void>(`/shot-groups/${groupId}/`)
}

export function createShotStatus(companyId: number, input: ShotStatusCreateIn) {
  return apiClient
    .post<ShotStatusOut>(`/companies/${companyId}/shot-statuses/`, input)
    .then((res) => res.data)
}

export function updateShotStatus(statusId: number, input: ShotStatusUpdateIn) {
  return apiClient
    .patch<ShotStatusOut>(`/shot-statuses/${statusId}/`, input)
    .then((res) => res.data)
}

export function deleteShotStatus(statusId: number) {
  return apiClient.delete<void>(`/shot-statuses/${statusId}/`)
}
