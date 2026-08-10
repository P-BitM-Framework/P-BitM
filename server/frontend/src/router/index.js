// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Login from '@/views/Login.vue'

const viewLoaders = {
  campaigns: () => import('@/views/Campaign.vue'),
  campaign: () => import('@/views/Dashboard.vue'),
  victim: () => import('@/views/DashboardVictim.vue'),
  'target-lists': () => import('@/views/TargetLists.vue'),
  'target-list': () => import('@/views/TargetListDetail.vue'),
  'email-templates': () => import('@/views/EmailTemplates.vue'),
  'smtp-profiles': () => import('@/views/SmtpProfiles.vue'),
  plugins: () => import('@/views/Plugins.vue'),
  'plugin-editor': () => import('@/views/PluginDetail.vue'),
  'landing-pages': () => import('@/views/LandingPages.vue'),
  modules: () => import('@/views/Modules.vue'),
  users: () => import('@/views/Users.vue')
}

export function preloadRouteComponent(routeName) {
  const loader = viewLoaders[routeName]
  return loader ? loader() : Promise.resolve()
}

export function preloadAuthenticatedRoutes() {
  return Promise.allSettled(Object.values(viewLoaders).map((loader) => loader()))
}

const routes = [
  { path: '/', redirect: '/campaigns' },
  { path: '/login', name: 'login', component: Login },
  { path: '/campaigns', name: 'campaigns', component: viewLoaders.campaigns, meta: { requiresAuth: true } },
  { path: '/campaigns/:campaignId', name: 'campaign', component: viewLoaders.campaign, meta: { requiresAuth: true } },
  { path: '/campaigns/:campaignId/victims/:victimId', name: 'victim', component: viewLoaders.victim, meta: { requiresAuth: true } },
  { path: '/target-lists', name: 'target-lists', component: viewLoaders['target-lists'], meta: { requiresAuth: true } },
  { path: '/target-lists/:listId', name: 'target-list', component: viewLoaders['target-list'], meta: { requiresAuth: true } },
  { path: '/email-templates', name: 'email-templates', component: viewLoaders['email-templates'], meta: { requiresAuth: true } },
  { path: '/smtp-profiles', name: 'smtp-profiles', component: viewLoaders['smtp-profiles'], meta: { requiresAuth: true } },
  { path: '/plugins', name: 'plugins', component: viewLoaders.plugins, meta: { requiresAuth: true } },
  { path: '/plugins/:id/edit', name: 'plugin-editor', component: viewLoaders['plugin-editor'], meta: { requiresAuth: true } },
  { path: '/landing-pages', name: 'landing-pages', component: viewLoaders['landing-pages'], meta: { requiresAuth: true } },
  { path: '/modules', name: 'modules', component: viewLoaders.modules, meta: { requiresAuth: true } },
  { path: '/users', name: 'users', component: viewLoaders.users, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/:pathMatch(.*)*', redirect: '/campaigns' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.checked) {
    await auth.checkAuth()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  } else if (to.meta.requiresAdmin && !auth.isAdmin) {
    return '/campaigns'
  } else if ((to.path === '/login' || to.path === '/register') && auth.isAuthenticated) {
    return '/'
  }
  return true
})

router.onError((error, to) => {
  const isChunkLoadError = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(error?.message || '')
  if (!isChunkLoadError) return

  const reloadKey = `bitm-chunk-reload:${to.fullPath}`
  if (!sessionStorage.getItem(reloadKey)) {
    sessionStorage.setItem(reloadKey, '1')
    window.location.assign(to.fullPath)
  }
})

router.afterEach((to) => {
  sessionStorage.removeItem(`bitm-chunk-reload:${to.fullPath}`)
})

export default router
