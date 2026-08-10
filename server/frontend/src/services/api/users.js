import { USER_API } from './endpoints'

export function createUsersClient(apiClient) {
  return {
    async getUsers() {
      return await apiClient.request(USER_API)
    },

    async createUser(data) {
      return await apiClient.request(USER_API, {
        method: 'POST',
        body: JSON.stringify(data)
      })
    },

    async updateUser(id, data) {
      return await apiClient.request(`${USER_API}/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
      })
    },

    async resetUserPassword(id) {
      return await apiClient.request(`${USER_API}/${id}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({})
      })
    },

    async changePassword(oldPassword) {
      return await apiClient.request(`${USER_API}/change-password`, {
        method: 'POST',
        body: JSON.stringify({ old_password: oldPassword })
      })
    },

    async deleteUser(id) {
      return await apiClient.request(`${USER_API}/${id}`, {
        method: 'DELETE'
      })
    }
  }
}
