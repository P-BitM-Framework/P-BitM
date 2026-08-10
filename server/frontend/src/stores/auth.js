// src/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { backendService } from '@/services/backend'

// One-time cleanup for browsers that used the legacy JWT-based frontend.
try {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
} catch {
  // Storage can be unavailable in hardened/private browser contexts.
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const csrfToken = ref(null)

  // Getters
  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canManage = computed(() => ['admin', 'operator'].includes(user.value?.role))

  // Actions
  function setSession(newUser, newCsrfToken) {
    user.value = newUser
    csrfToken.value = newCsrfToken
  }

  function logout() {
    user.value = null
    csrfToken.value = null
  }

  const checked = ref(false)

  async function checkAuth() {
    try {
      const response = await backendService.getUserProfile()
      setSession(response.user, response.csrf_token)
      checked.value = true
      return true
    } catch (_error) {
      logout()
      checked.value = true
      return false
    }
  }

  return {
    user,
    csrfToken,
    isAuthenticated,
    isAdmin,
    canManage,
    setSession,
    logout,
    checkAuth,
    checked
  }
})
