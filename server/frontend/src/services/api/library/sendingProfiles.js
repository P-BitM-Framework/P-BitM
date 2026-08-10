import { SENDING_PROFILE_API } from '../endpoints'
import { pickPayloadFields } from './payloads'

const CREATE_FIELDS = [
  'name',
  'description',
  'smtp_host',
  'smtp_port',
  'smtp_username',
  'smtp_password',
  'smtp_use_tls',
  'smtp_use_ssl',
  'ignore_cert_errors',
  'from_email',
  'from_name',
  'domain',
  'tracking_domain',
  'dkim_enabled',
  'dkim_selector',
  'dkim_private_key'
]
const UPDATE_FIELDS = [...CREATE_FIELDS, 'is_active']

export function smtpProfilePayload(data, { update = false } = {}) {
  const payload = pickPayloadFields(data, update ? UPDATE_FIELDS : CREATE_FIELDS)

  if (Object.prototype.hasOwnProperty.call(data || {}, 'encryption')) {
    payload.smtp_use_tls = ['tls', 'starttls'].includes(data.encryption)
    payload.smtp_use_ssl = data.encryption === 'ssl'
    if (!payload.smtp_use_tls && !payload.smtp_use_ssl) {
      payload.ignore_cert_errors = false
    }
  }

  if (update) {
    for (const secret of ['smtp_password', 'dkim_private_key']) {
      if (payload[secret] === '') delete payload[secret]
    }
  }
  return payload
}

export function createSendingProfilesClient(apiClient) {
  return {
    async getSMTPProfiles() {
      return await apiClient.request(SENDING_PROFILE_API)
    },

    async getSMTPProfile(id) {
      return await apiClient.request(`${SENDING_PROFILE_API}/${id}`)
    },

    async createSMTPProfile(data) {
      return await apiClient.request(SENDING_PROFILE_API, {
        method: 'POST',
        body: JSON.stringify(smtpProfilePayload(data))
      })
    },

    async updateSMTPProfile(id, data) {
      return await apiClient.request(`${SENDING_PROFILE_API}/${id}`, {
        method: 'PUT',
        body: JSON.stringify(smtpProfilePayload(data, { update: true }))
      })
    },

    async deleteSMTPProfile(id) {
      return await apiClient.request(`${SENDING_PROFILE_API}/${id}`, {
        method: 'DELETE'
      })
    },

    async testSMTPProfile(id) {
      return await apiClient.request(`${SENDING_PROFILE_API}/${id}/test`, {
        method: 'POST'
      })
    }
  }
}
