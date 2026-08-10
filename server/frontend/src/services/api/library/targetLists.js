import { TARGET_LIST_API } from '../endpoints'
import { pickPayloadFields } from './payloads'

const TARGET_LIST_FIELDS = ['name', 'description', 'company']
const TARGET_FIELDS = [
  'email',
  'first_name',
  'last_name',
  'position',
  'department',
  'custom_fields'
]

export function targetListPayload(data) {
  return pickPayloadFields(data, TARGET_LIST_FIELDS)
}

export function targetPayload(data) {
  return pickPayloadFields(data, TARGET_FIELDS)
}

export function createTargetListsClient(apiClient) {
  return {
    async getTargetLists() {
      return await apiClient.request(TARGET_LIST_API)
    },

    async getTargetList(id) {
      return await apiClient.request(`${TARGET_LIST_API}/${id}`)
    },

    async createTargetList(data) {
      return await apiClient.request(TARGET_LIST_API, {
        method: 'POST',
        body: JSON.stringify(targetListPayload(data))
      })
    },

    async updateTargetList(id, data) {
      return await apiClient.request(`${TARGET_LIST_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(targetListPayload(data))
      })
    },

    async deleteTargetList(id) {
      return await apiClient.request(`${TARGET_LIST_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async addTarget(listId, target) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/targets`, {
        method: 'POST',
        body: JSON.stringify(targetPayload(target))
      })
    },

    async getTargets(listId) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/targets`)
    },

    async updateTarget(listId, targetId, target) {
      return await apiClient.request(
        `${TARGET_LIST_API}/${listId}/targets/${targetId}`,
        {
          method: 'PUT',
          body: JSON.stringify(targetPayload(target))
        }
      )
    },

    async bulkAddTargets(listId, targets) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/targets/bulk`, {
        method: 'POST',
        body: JSON.stringify({ targets })
      })
    },

    async bulkDeleteTargets(listId, targetIds) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/targets/bulk-delete`, {
        method: 'POST',
        body: JSON.stringify({ target_ids: targetIds })
      })
    },

    async deleteTarget(listId, targetId) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/targets/${targetId}`, {
        method: 'DELETE'
      })
    },

    async exportTargetsCsv(listId) {
      return await apiClient.request(`${TARGET_LIST_API}/${listId}/export-csv`, {
        responseType: 'blob',
        headers: {
          Accept: 'text/csv'
        }
      })
    }
  }
}
