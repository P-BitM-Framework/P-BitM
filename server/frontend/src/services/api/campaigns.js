import { CAMPAIGN_API } from './endpoints'

export function createCampaignsClient(apiClient) {
  return {
    async createCampaign(campaignData) {
      return await apiClient.request(CAMPAIGN_API, {
        method: 'POST',
        body: JSON.stringify(campaignData)
      })
    },

    async getCampaign(campaignId, options = {}) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}`, options)
    },

    async stopCampaign(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/stop`, {
        method: 'POST'
      })
    },

    async pauseCampaign(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/pause`, {
        method: 'POST'
      })
    },

    async resumeCampaign(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/resume`, {
        method: 'POST'
      })
    },

    async deleteCampaign(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}`, {
        method: 'DELETE'
      })
    },

    async getCampaigns(options = {}) {
      return await apiClient.request(CAMPAIGN_API, options)
    },

    async getCampaignAttacks(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/attacks`, {
        method: 'GET'
      })
    },

    async getCampaignModules(campaignId) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/modules`, {
        method: 'GET'
      })
    },

    async createCampaignModule(campaignId, data) {
      return await apiClient.request(`${CAMPAIGN_API}/${campaignId}/modules`, {
        method: 'POST',
        body: JSON.stringify(data)
      })
    }
  }
}
