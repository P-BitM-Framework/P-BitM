import { AUTH_API } from './endpoints'

export function createAuthClient(apiClient) {
  return {
    async login(username, password) {
      return await apiClient.request(`${AUTH_API}/login`, {
        method: 'POST',
        body: JSON.stringify({ username, password })
      })
    },

    async logout() {
      return await apiClient.request(`${AUTH_API}/logout`, {
        method: 'POST',
        suppressAuthRedirect: true
      })
    },

    async register(username, email, password) {
      return await apiClient.request(`${AUTH_API}/register`, {
        method: 'POST',
        body: JSON.stringify({ username, email, password })
      })
    },

    async getUserProfile() {
      return await apiClient.request(`${AUTH_API}/me`, {
        suppressAuthRedirect: true
      })
    }
  }
}
