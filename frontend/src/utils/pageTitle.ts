import type { RouteLocationNormalized } from 'vue-router'

export const APP_NAME = 'Паприка'

const SEPARATOR = ' · '

export function buildPageTitle(parts: Array<string | null | undefined>): string {
  return [...parts.filter((part): part is string => Boolean(part)), APP_NAME].join(SEPARATOR)
}

export function routePageTitle(route: Pick<RouteLocationNormalized, 'meta' | 'params'>): string {
  const title = typeof route.meta.title === 'string' ? route.meta.title : undefined
  const shotName = typeof route.params.shotName === 'string' ? route.params.shotName : undefined
  const projectCode =
    typeof route.params.projectCode === 'string' ? route.params.projectCode : undefined

  if (shotName) return buildPageTitle([shotName, title])
  return buildPageTitle([title, projectCode])
}
