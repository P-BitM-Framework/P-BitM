import { LANDING_PAGE_API } from '../endpoints'
import { downloadFile } from '../http'
import { pickPayloadFields } from './payloads'

const LANDING_PAGE_FIELDS = ['name', 'description', 'content']

export function landingPagePayload(data) {
  return pickPayloadFields(data, LANDING_PAGE_FIELDS)
}

export function createLandingPagesClient(apiClient) {
  return {
    async getLandingPages() {
      return await apiClient.request(LANDING_PAGE_API, { method: 'GET' })
    },

    async getLandingPage(id) {
      return await apiClient.request(`${LANDING_PAGE_API}/${id}`, { method: 'GET' })
    },

    async createLandingPage(data) {
      return await apiClient.request(LANDING_PAGE_API, {
        method: 'POST',
        body: JSON.stringify(landingPagePayload(data))
      })
    },

    async updateLandingPage(id, data) {
      return await apiClient.request(`${LANDING_PAGE_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(landingPagePayload(data))
      })
    },

    async deleteLandingPage(id) {
      return await apiClient.request(`${LANDING_PAGE_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async exportLandingPage(id) {
      const response = await apiClient.request(`${LANDING_PAGE_API}/${id}/export`, {
        method: 'GET',
        responseType: 'blob'
      })
      downloadFile(response.data, `landing-page-${id}.html`)
    },

    async importLandingPage(formData) {
      return await apiClient.request(`${LANDING_PAGE_API}/import`, {
        method: 'POST',
        body: formData
      })
    },

    async cloneLandingPage(id) {
      return await apiClient.request(`${LANDING_PAGE_API}/${id}/clone`, {
        method: 'POST'
      })
    }
  }
}
