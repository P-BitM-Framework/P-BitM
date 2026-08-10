import { describe, expect, it, vi } from 'vitest'

import { createCampaignsClient } from '@/services/api/campaigns'


describe('campaign runtime client', () => {
  it.each([
    ['pauseCampaign', 'api/campaigns/campaign-1/pause'],
    ['resumeCampaign', 'api/campaigns/campaign-1/resume']
  ])('sends %s as a POST request', async (method, endpoint) => {
    const apiClient = {
      request: vi.fn().mockResolvedValue({ status: 'ok' })
    }
    const client = createCampaignsClient(apiClient)

    await client[method]('campaign-1')

    expect(apiClient.request).toHaveBeenCalledWith(endpoint, {
      method: 'POST'
    })
  })
})
