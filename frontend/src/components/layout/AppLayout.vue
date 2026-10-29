<script setup lang="ts">
import { computed, h, ref } from 'vue'
import { useBreakpoints, breakpointsTailwind } from '@vueuse/core'
import { NIcon, type MenuOption } from 'naive-ui'
import {
  PeopleOutline,
  BusinessOutline,
  FilmOutline,
  MoonOutline,
  SunnyOutline,
  MenuOutline,
  LogOutOutline,
  KeyOutline,
} from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import CompanySwitcher from '@/components/layout/CompanySwitcher.vue'
import { setAppHeaderSlot } from '@/composables/useAppHeaderSlot'

const ui = useUiStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const breakpoints = useBreakpoints(breakpointsTailwind)
// Below `lg` (1024px) we stop trying to squeeze the sidebar into a
// narrow column and use an overlay drawer instead - a half-width
// sidebar on a tablet is worse than no persistent sidebar at all.
const isMobile = breakpoints.smaller('lg')

const mobileDrawerOpen = ref(false)

const currentUserInitials = computed(() => {
  const user = auth.currentUser
  if (!user) return '?'
  return `${user.first_name[0] ?? ''}${user.last_name[0] ?? ''}`.toUpperCase() || '?'
})

function renderIcon(icon: object) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed<MenuOption[]>(() => [
  // Accounts are the server administrator's business; everyone else adds
  // people through their company.
  ...(auth.isSuperuser
    ? [{ label: 'Пользователи', key: 'users-list', icon: renderIcon(PeopleOutline) }]
    : []),
  {
    label: 'Проекты',
    key: 'project-list',
    icon: renderIcon(FilmOutline),
  },
  {
    label: 'Компании',
    key: 'company-list',
    icon: renderIcon(BusinessOutline),
  },
])

const activeKey = computed(() => {
  if (route.name === 'users-list') return 'users-list'
  if (route.name === 'project-list' || route.name === 'project-create') return 'project-list'
  if (route.name === 'company-list' || route.name === 'company-create') return 'company-list'
  return null
})

function handleMenuSelect(key: string) {
  router.push({ name: key })
  mobileDrawerOpen.value = false
}

async function handleUserMenu(key: string) {
  if (key === 'change-password') {
    router.push({ name: 'change-password' })
    return
  }
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <n-layout style="height: 100vh" has-sider>
    <n-layout-sider
      v-if="!isMobile"
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="ui.sidebarCollapsed"
      show-trigger
      @collapse="ui.sidebarCollapsed = true"
      @expand="ui.sidebarCollapsed = false"
    >
      <div class="sider-content">
        <div class="sider-content__scroll">
          <div class="brand" :class="{ 'brand--collapsed': ui.sidebarCollapsed }">
            <span class="brand__mark">P</span>
            <span v-if="!ui.sidebarCollapsed" class="brand__name">Paprika</span>
          </div>
          <n-menu
            :collapsed="ui.sidebarCollapsed"
            :collapsed-width="64"
            :options="menuOptions"
            :value="activeKey"
            @update:value="handleMenuSelect"
          />
        </div>
        <company-switcher :collapsed="ui.sidebarCollapsed" />
      </div>
    </n-layout-sider>

    <n-drawer v-else v-model:show="mobileDrawerOpen" placement="left" :width="240">
      <n-drawer-content title="Paprika" closable>
        <n-menu :options="menuOptions" :value="activeKey" @update:value="handleMenuSelect" />
        <template #footer>
          <company-switcher />
        </template>
      </n-drawer-content>
    </n-drawer>

    <n-layout>
      <n-layout-header bordered class="app-header">
        <n-button v-if="isMobile" quaternary circle @click="mobileDrawerOpen = true">
          <template #icon><n-icon :component="MenuOutline" /></template>
        </n-button>
        <span v-if="isMobile" class="app-header__brand">Paprika</span>

        <div :ref="setAppHeaderSlot" class="app-header__slot" />

        <div class="app-header__spacer" />

        <n-button quaternary circle title="Переключить тему" @click="ui.toggleTheme">
          <template #icon>
            <n-icon :component="ui.isDark ? SunnyOutline : MoonOutline" />
          </template>
        </n-button>

        <n-dropdown
          trigger="click"
          :options="[
            { label: 'Сменить пароль', key: 'change-password', icon: renderIcon(KeyOutline) },
            { label: 'Выйти', key: 'logout', icon: renderIcon(LogOutOutline) },
          ]"
          @select="handleUserMenu"
        >
          <button class="user-menu-trigger" type="button">
            <n-avatar
              round
              :size="32"
              :src="auth.currentUser?.avatar ?? undefined"
              style="font-family: var(--font-mono); font-size: 12px"
            >
              <template v-if="!auth.currentUser?.avatar">{{ currentUserInitials }}</template>
            </n-avatar>
          </button>
        </n-dropdown>
      </n-layout-header>

      <n-layout-content class="app-content">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<style scoped>
.sider-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sider-content__scroll {
  flex: 1;
  overflow-y: auto;
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  font-weight: 600;
}

.brand--collapsed {
  justify-content: center;
  padding: var(--space-4) 0;
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-accent-text);
  font-family: var(--font-mono);
  font-weight: 700;
}

.app-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  height: 56px;
}

.app-header__brand {
  font-weight: 600;
}

.app-header__slot {
  display: flex;
  align-items: center;
  align-self: stretch;
  gap: var(--space-3);
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.app-header__slot:empty {
  display: none;
}

.app-header__spacer {
  flex: 1;
}

.user-menu-trigger {
  display: inline-flex;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: none;
  cursor: pointer;
  line-height: 0;
}

.user-menu-trigger:hover {
  opacity: 0.85;
}

.app-content {
  padding: var(--space-5);
  height: calc(100vh - 56px);
  overflow-y: auto;
}

@media (max-width: 640px) {
  .app-content {
    padding: var(--space-4);
  }
}
</style>
