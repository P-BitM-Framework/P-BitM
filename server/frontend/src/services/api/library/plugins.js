import { PLUGIN_API } from '../endpoints'
import { downloadFile } from '../http'

export function createPluginsClient(apiClient) {
  return {
    async getPlugins() {
      return await apiClient.request(PLUGIN_API, { method: 'GET' })
    },

    async getPlugin(id) {
      return await apiClient.request(`${PLUGIN_API}/${id}`, { method: 'GET' })
    },

    async createPlugin(data) {
      return await apiClient.request(PLUGIN_API, {
        method: 'POST',
        body: JSON.stringify(data)
      })
    },

    async updatePlugin(id, data) {
      return await apiClient.request(`${PLUGIN_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      })
    },

    async deletePlugin(id) {
      return await apiClient.request(`${PLUGIN_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async exportPlugin(id) {
      const response = await apiClient.request(`${PLUGIN_API}/${id}/export`, {
        method: 'GET',
        responseType: 'blob'
      })
      downloadFile(response.data, `plugin-${id}.zip`)
    },

    async importPlugin(formData) {
      return await apiClient.request(`${PLUGIN_API}/import`, {
        method: 'POST',
        body: formData
      })
    }
  }
}
