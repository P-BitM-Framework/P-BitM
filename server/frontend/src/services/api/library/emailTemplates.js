import { EMAIL_TEMPLATE_API } from '../endpoints'
import { pickPayloadFields } from './payloads'

const CREATE_FIELDS = [
  'name',
  'description',
  'subject',
  'html_content',
  'text_content',
  'category',
  'tags',
  'attachments',
  'variables'
]
const UPDATE_FIELDS = [...CREATE_FIELDS, 'is_active']

export function emailTemplatePayload(data, { update = false } = {}) {
  return pickPayloadFields(data, update ? UPDATE_FIELDS : CREATE_FIELDS)
}

export function createEmailTemplatesClient(apiClient) {
  return {
    async getEmailTemplates() {
      return await apiClient.request(EMAIL_TEMPLATE_API)
    },

    async getEmailTemplate(id) {
      return await apiClient.request(`${EMAIL_TEMPLATE_API}/${id}`)
    },

    async createEmailTemplate(data) {
      return await apiClient.request(EMAIL_TEMPLATE_API, {
        method: 'POST',
        body: JSON.stringify(emailTemplatePayload(data))
      })
    },

    async updateEmailTemplate(id, data) {
      return await apiClient.request(`${EMAIL_TEMPLATE_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(emailTemplatePayload(data, { update: true }))
      })
    },

    async deleteEmailTemplate(id) {
      return await apiClient.request(`${EMAIL_TEMPLATE_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async toggleTemplateFavorite(id) {
      return await apiClient.request(`${EMAIL_TEMPLATE_API}/${id}/favorite`, {
        method: 'PATCH'
      })
    },

    async cloneEmailTemplate(id, data) {
      const newName = typeof data === 'string' ? data : data?.name
      return await apiClient.request(
        `${EMAIL_TEMPLATE_API}/${id}/duplicate?new_name=${encodeURIComponent(newName || '')}`,
        {
        method: 'POST'
        }
      )
    }
  }
}
