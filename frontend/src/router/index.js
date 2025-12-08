import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import ProjectCreate from '@/views/ProjectCreate.vue'
import ProjectList from '@/views/ProjectList.vue'
import ShotCreate from '@/views/ShotCreate.vue'
import ShotDetails from '@/views/ShotDetails.vue'
import ShotGroupCreate from '@/views/ShotGroupCreate.vue'
import ShotGroupDetails from '@/views/ShotGroupDetails.vue'
import ShotGroupList from '@/views/ShotGroupList.vue'
import ShotsList from '@/views/ShotsList2.vue'
import TaskDetails from '@/views/TaskDetails.vue'
import TaskList from '@/views/TaskList.vue'
import { ref } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: ProjectList,
      meta: { requiresAuth: true },
    },
    {
      path: '/projects/create',
      name: 'create-project',
      component: ProjectCreate,
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/shots',
      name: 'shots',
      component: ShotsList,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shots',
      name: 'shots-by-project',
      component: ShotsList,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shots/create',
      name: 'create-shots',
      component: ShotCreate,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shots/:shotName',
      name: 'shot-details',
      component: ShotDetails,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/tasks',
      name: 'tasks-by-project',
      component: TaskList,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/tasks/:taskId',
      name: 'task-details-by-project',
      component: TaskDetails,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shot-groups',
      name: 'shot-groups-by-project',
      component: ShotGroupList,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shot-groups/create',
      name: 'create-shot-groups',
      component: ShotGroupCreate,
      meta: { requiresAuth: true },
    },
    {
      path: '/:projectCode/shot-groups/:shotGroupId',
      name: 'shot-group-details-by-project',
      component: ShotGroupDetails,
      meta: { requiresAuth: true },
    },
  ],
})

export const previousRoute = ref(null)

router.beforeEach(async (to, from) => {
  previousRoute.value = from
  const auth = useAuthStore()

  if (to.meta.requiresAuth || to.name !== 'login') {
    if (!auth.isUserAuthenticated) {
      return {
        name: 'login',
        query: { next: to.fullPath },
      }
    }

    // Дополнительно проверяем валидность токена
    try {
      await auth.fetchUser()
    } catch (e) {
      auth.logout()
      return {
        name: 'login',
        query: { next: to.fullPath },
      }
    }
  }
})

export default router
