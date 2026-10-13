import { apiClient } from './client'
import type {
  ShotTaskCreateIn,
  ShotTaskListOut,
  ShotTaskOut,
  ShotTaskUpdateIn,
  TaskCreateIn,
  TaskListOut,
  TaskListQuery,
  TaskOut,
  TaskStatusListOut,
  TaskTypeListOut,
} from '@/types/api'

export function listTasks(projectId: number, query: TaskListQuery = {}) {
  return apiClient
    .get<TaskListOut>(`/projects/${projectId}/tasks/`, { params: query })
    .then((res) => res.data)
}

export function createTask(projectId: number, input: TaskCreateIn) {
  return apiClient.post<TaskOut>(`/projects/${projectId}/tasks/`, input).then((res) => res.data)
}

export function listTaskTypes(companyId: number) {
  return apiClient
    .get<TaskTypeListOut>(`/companies/${companyId}/task-types/`)
    .then((res) => res.data)
}

export function listTaskStatuses(companyId: number) {
  return apiClient
    .get<TaskStatusListOut>(`/companies/${companyId}/task-statuses/`)
    .then((res) => res.data)
}

export function listShotTasks(shotId: number) {
  return apiClient.get<ShotTaskListOut>(`/shots/${shotId}/tasks/`).then((res) => res.data)
}

export function createShotTask(shotId: number, input: ShotTaskCreateIn) {
  return apiClient.post<ShotTaskOut>(`/shots/${shotId}/tasks/`, input).then((res) => res.data)
}

export function updateShotTask(shotTaskId: number, input: ShotTaskUpdateIn) {
  return apiClient.patch<ShotTaskOut>(`/shot-tasks/${shotTaskId}/`, input).then((res) => res.data)
}

export function deleteShotTask(shotTaskId: number) {
  return apiClient.delete<void>(`/shot-tasks/${shotTaskId}/`)
}
