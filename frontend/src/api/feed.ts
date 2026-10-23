import { apiClient } from './client'
import type { FeedOut, FeedQuery } from '@/types/api'

export function listFeed(projectId: number, query: FeedQuery = {}) {
  return apiClient
    .get<FeedOut>(`/projects/${projectId}/feed/`, { params: query })
    .then((res) => res.data)
}
