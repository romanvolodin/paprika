import { useAuthStore } from '@/stores/auth'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'
import ProjectList from '@/views/ProjectList.vue'
import ProjectCreate from '@/views/ProjectCreate.vue'
import ShotsList from '@/views/ShotsList.vue'
import ShotDetails from '@/views/ShotDetails.vue'
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
      path: '/:projectCode/shots/:shotName',
      name: 'shot-details',
      component: ShotDetails,
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
