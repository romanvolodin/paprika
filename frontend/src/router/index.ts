import { createRouter, createWebHistory } from 'vue-router'
import { setupAuthGuard } from './guards'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    // Rendered full-screen, without the sidebar/header AppShell.
    standalone?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { standalone: true },
    },
    {
      path: '/',
      redirect: { name: 'users-list' },
    },
    {
      path: '/users',
      name: 'users-list',
      component: () => import('@/views/UsersListView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/users/new',
      name: 'user-create',
      component: () => import('@/views/UserFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/users/:id(\\d+)',
      name: 'user-detail',
      component: () => import('@/views/UserFormView.vue'),
      props: (route) => ({ userId: Number(route.params.id) }),
      meta: { requiresAuth: true },
    },
    {
      path: '/companies',
      name: 'company-list',
      component: () => import('@/views/CompaniesListView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/companies/new',
      name: 'company-create',
      component: () => import('@/views/CompanyFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/companies/:id(\\d+)',
      name: 'company-detail',
      component: () => import('@/views/CompanyDetailView.vue'),
      props: (route) => ({ companyId: Number(route.params.id) }),
      meta: { requiresAuth: true },
    },
    {
      path: '/projects',
      name: 'project-list',
      component: () => import('@/views/ProjectsListView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: () => import('@/views/ProjectFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/projects/:id(\\d+)',
      name: 'project-detail',
      component: () => import('@/views/ProjectDetailView.vue'),
      props: (route) => ({ projectId: Number(route.params.id) }),
      meta: { requiresAuth: true },
    },
    {
      path: '/:companySlug/:projectCode/shots',
      name: 'shot-list',
      component: () => import('@/views/ShotListView.vue'),
      props: (route) => ({
        companySlug: String(route.params.companySlug),
        projectCode: String(route.params.projectCode),
      }),
      meta: { requiresAuth: true },
    },
    {
      path: '/:companySlug/:projectCode/shots/import',
      name: 'shot-import',
      component: () => import('@/views/ShotImportView.vue'),
      props: (route) => ({
        companySlug: String(route.params.companySlug),
        projectCode: String(route.params.projectCode),
      }),
      meta: { requiresAuth: true },
    },
    {
      path: '/:companySlug/:projectCode/shots/:shotName',
      name: 'shot-detail',
      component: () => import('@/views/ShotDetailView.vue'),
      props: (route) => ({
        companySlug: String(route.params.companySlug),
        projectCode: String(route.params.projectCode),
        shotName: String(route.params.shotName),
      }),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { standalone: true },
    },
  ],
})

setupAuthGuard(router)

export default router
