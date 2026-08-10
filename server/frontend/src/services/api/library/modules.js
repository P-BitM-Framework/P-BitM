import { MODULE_API } from '../endpoints'
import { downloadFile } from '../http'
import { pickPayloadFields } from './payloads'

const MODULE_FIELDS = [
  'name',
  'description',
  'category',
  'icon',
  'inputs',
  'payload',
  'link'
]
const MODULE_INPUT_FIELDS = ['id', 'label', 'type', 'required']

export function modulePayload(data) {
  const payload = pickPayloadFields(data, MODULE_FIELDS)
  if (Array.isArray(payload.inputs)) {
    payload.inputs = payload.inputs.map((input) =>
      pickPayloadFields(input, MODULE_INPUT_FIELDS)
    )
  }
  return payload
}

export function createModulesClient(apiClient) {
  return {
    async getModules() {
      return await apiClient.request(MODULE_API, { method: 'GET' })
    },

    async getModule(id) {
      return await apiClient.request(`${MODULE_API}/${id}`, { method: 'GET' })
    },

    async createModule(data) {
      return await apiClient.request(MODULE_API, {
        method: 'POST',
        body: JSON.stringify(modulePayload(data))
      })
    },

    async updateModule(id, data) {
      return await apiClient.request(`${MODULE_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(modulePayload(data))
      })
    },

    async deleteModule(id) {
      return await apiClient.request(`${MODULE_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async exportModule(id) {
      const response = await apiClient.request(`${MODULE_API}/${id}/export`, {
        method: 'GET',
        responseType: 'blob'
      })
      downloadFile(response.data, `module-${id}.json`)
    },

    async cloneModule(id) {
      return await apiClient.request(`${MODULE_API}/${id}/clone`, {
        method: 'POST'
      })
    }
  }
}
