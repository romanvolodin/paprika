import { createRouter, createWebHistory } from 'vue-router'
import { setupAuthGuard } from './guards'
import { routePageTitle } from '@/utils/pageTitle'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    // Rendered full-screen, without the sidebar/header AppShell.
    standalone?: boolean
    // Tab title of the page; the shot name / project code and the app name are added around it.
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Вход', standalone: true },
    },
    {
      path: '/',
      redirect: { name: 'project-list' },
    },
    {
      path: '/users',
      name: 'users-list',
      component: () => import('@/views/UsersListView.vue'),
      meta: { title: 'Пользователи', requiresAuth: true },
    },
    {
      path: '/users/new',
      name: 'user-create',
      component: () => import('@/views/UserFormView.vue'),
      meta: { title: 'Новый пользователь', requiresAuth: true },
    },
    {
      path: '/users/:id(\\d+)',
      name: 'user-detail',
      component: () => import('@/views/UserFormView.vue'),
      props: (route) => ({ userId: Number(route.params.id) }),
      meta: { title: 'Пользователь', requiresAuth: true },
    },
    {
      path: '/companies',
      name: 'company-list',
      component: () => import('@/views/CompaniesListView.vue'),
      meta: { title: 'Компании', requiresAuth: true },
    },
    {
      path: '/companies/new',
      name: 'company-create',
      component: () => import('@/views/CompanyFormView.vue'),
      meta: { title: 'Новая компания', requiresAuth: true },
    },
    {
      path: '/companies/:id(\\d+)',
      name: 'company-detail',
      component: () => import('@/views/CompanyDetailView.vue'),
      props: (route) => ({ companyId: Number(route.params.id) }),
      meta: { title: 'Компания', requiresAuth: true },
    },
    {
      path: '/projects',
      name: 'project-list',
      component: () => import('@/views/ProjectsListView.vue'),
      meta: { title: 'Проекты', requiresAuth: true },
    },
    {
      path: '/projects/new',
      name: 'project-create',
      component: () => import('@/views/ProjectFormView.vue'),
      meta: { title: 'Новый проект', requiresAuth: true },
    },
    {
      path: '/:companySlug/:projectCode',
      component: () => import('@/views/ProjectLayoutView.vue'),
      props: (route) => ({
        companySlug: String(route.params.companySlug),
        projectCode: String(route.params.projectCode),
      }),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'project-home',
          redirect: (to) => ({ name: 'shot-list', params: to.params }),
        },
        {
          path: 'feed',
          name: 'project-feed',
          meta: { title: 'Лента' },
          component: () => import('@/views/ProjectFeedView.vue'),
        },
        {
          path: 'shots',
          name: 'shot-list',
          meta: { title: 'Кадры' },
          component: () => import('@/views/ShotListView.vue'),
          props: (route) => ({
            companySlug: String(route.params.companySlug),
            projectCode: String(route.params.projectCode),
          }),
        },
        {
          path: 'shots/import',
          name: 'shot-import',
          meta: { title: 'Импорт кадров' },
          component: () => import('@/views/ShotImportView.vue'),
          props: (route) => ({
            companySlug: String(route.params.companySlug),
            projectCode: String(route.params.projectCode),
          }),
        },
        {
          path: 'shots/:shotName',
          component: () => import('@/views/ShotLayoutView.vue'),
          props: (route) => ({
            companySlug: String(route.params.companySlug),
            projectCode: String(route.params.projectCode),
            shotName: String(route.params.shotName),
          }),
          children: [
            {
              path: '',
              name: 'shot-detail',
              meta: { title: 'Просмотр' },
              component: () => import('@/views/ShotReviewView.vue'),
            },
            {
              path: 'tasks',
              name: 'shot-tasks',
              meta: { title: 'Задачи' },
              component: () => import('@/views/ShotTasksView.vue'),
            },
            {
              path: 'versions',
              name: 'shot-versions',
              meta: { title: 'Версии' },
              component: () => import('@/views/ShotVersionsView.vue'),
            },
            {
              path: 'upload',
              name: 'shot-upload',
              meta: { title: 'Загрузка' },
              component: () => import('@/views/ShotUploadView.vue'),
            },
            {
              path: 'settings',
              name: 'shot-settings',
              meta: { title: 'Настройки' },
              component: () => import('@/views/ShotSettingsView.vue'),
              props: (route) => ({
                companySlug: String(route.params.companySlug),
                projectCode: String(route.params.projectCode),
              }),
            },
          ],
        },
        {
          path: 'tasks',
          name: 'project-tasks',
          meta: { title: 'Задачи' },
          component: () => import('@/views/ProjectTasksView.vue'),
        },
        {
          path: 'groups',
          name: 'project-groups',
          meta: { title: 'Группы' },
          component: () => import('@/views/ProjectGroupsView.vue'),
        },
        {
          path: 'settings',
          name: 'project-settings',
          meta: { title: 'Настройки' },
          component: () => import('@/views/ProjectSettingsView.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: 'Страница не найдена', standalone: true },
    },
  ],
})

setupAuthGuard(router)

router.afterEach((to) => {
  document.title = routePageTitle(to)
})

export default router
