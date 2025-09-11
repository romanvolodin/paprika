import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'
import ProjectCreate from '@/views/ProjectCreate.vue'
import ProjectList from '@/views/ProjectList.vue'
import ShotCreate from '@/views/ShotCreate.vue'
import ShotDetails from '@/views/ShotDetails.vue'
import ShotGroupDetails from '@/views/ShotGroupDetails.vue'
import ShotGroupList from '@/views/ShotGroupList.vue'
import ShotsList from '@/views/ShotsList.vue'
import TaskDetails from '@/views/TaskDetails.vue'
import TaskList from '@/views/TaskList.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: ProjectList,
    },
    {
      path: '/projects/create',
      name: 'create-project',
      component: ProjectCreate,
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
    },
    {
      path: '/:projectCode/shots',
      name: 'shots-by-project',
      component: ShotsList,
    },
    {
      path: '/:projectCode/shots/create',
      name: 'create-shots',
      component: ShotCreate,
    },
    {
      path: '/:projectCode/shots/:shotName',
      name: 'shot-details',
      component: ShotDetails,
    },
    {
      path: '/:projectCode/tasks',
      name: 'tasks-by-project',
      component: TaskList,
    },
    {
      path: '/:projectCode/tasks/:taskId',
      name: 'task-details-by-project',
      component: TaskDetails,
    },
    {
      path: '/:projectCode/shot-groups',
      name: 'shot-groups-by-project',
      component: ShotGroupList,
    },
    {
      path: '/:projectCode/shot-groups/:shotGroupId',
      name: 'shot-group-details-by-project',
      component: ShotGroupDetails,
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.isUserAuthenticated && to.name !== 'login') {
    return {
      name: 'login',
      query: { next: to.fullPath },
    }
  }
})

export default router
