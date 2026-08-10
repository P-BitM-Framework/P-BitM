import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  router: {
    push: vi.fn()
  },
  authStore: {
    csrfToken: 'csrf-token',
    logout: vi.fn()
  }
}))

vi.mock('@/router', () => ({
  default: mocks.router
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mocks.authStore
}))

import { createApiClient } from '@/services/api/http'

function mockResponse({
  status = 200,
  statusText = 'OK',
  contentType = 'application/json',
  json = {},
  text = '',
  blob = new Blob(['blob'])
} = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    headers: new Headers(contentType ? { 'content-type': contentType } : {}),
    json: vi.fn().mockResolvedValue(json),
    text: vi.fn().mockResolvedValue(text),
    blob: vi.fn().mockResolvedValue(blob)
  }
}

describe('createApiClient', () => {
  let apiClient

  beforeEach(() => {
    apiClient = createApiClient('https://admin.example/')
    mocks.authStore.csrfToken = 'csrf-token'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse()))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends same-origin credentials and merges request headers', async () => {
    await apiClient.request('api/campaigns', {
      headers: { Accept: 'application/json' },
      credentials: 'omit'
    })

    expect(fetch).toHaveBeenCalledWith('https://admin.example/api/campaigns', {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      },
      credentials: 'include'
    })
  })

  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])(
    'adds the CSRF token to %s requests',
    async (method) => {
      await apiClient.request('api/resource', { method })

      expect(fetch).toHaveBeenCalledWith(
        'https://admin.example/api/resource',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-CSRF-Token': 'csrf-token'
          })
        })
      )
    }
  )

  it.each(['GET', 'HEAD', 'OPTIONS'])(
    'does not add a CSRF header to %s requests',
    async (method) => {
      await apiClient.request('api/resource', { method })

      const [, requestOptions] = fetch.mock.calls[0]
      expect(requestOptions.headers).not.toHaveProperty('X-CSRF-Token')
    }
  )

  it('does not add an empty CSRF header to a mutation', async () => {
    mocks.authStore.csrfToken = null

    await apiClient.request('api/resource', { method: 'POST' })

    const [, requestOptions] = fetch.mock.calls[0]
    expect(requestOptions.headers).not.toHaveProperty('X-CSRF-Token')
  })

  it('lets the browser set multipart boundaries for FormData', async () => {
    const body = new FormData()
    body.append('file', new Blob(['content']), 'example.txt')

    await apiClient.request('api/import', {
      method: 'POST',
      body,
      headers: { Accept: 'application/json' }
    })

    const [, requestOptions] = fetch.mock.calls[0]
    expect(requestOptions.body).toBe(body)
    expect(requestOptions.headers).toEqual({
      Accept: 'application/json',
      'X-CSRF-Token': 'csrf-token'
    })
  })

  it('parses JSON, text and image responses according to content type', async () => {
    const jsonResponse = mockResponse({ json: { id: 'campaign-1' } })
    const textResponse = mockResponse({
      contentType: 'text/plain',
      text: 'ready'
    })
    const imageBlob = new Blob(['image'], { type: 'image/png' })
    const imageResponse = mockResponse({
      contentType: 'image/png',
      blob: imageBlob
    })
    fetch
      .mockResolvedValueOnce(jsonResponse)
      .mockResolvedValueOnce(textResponse)
      .mockResolvedValueOnce(imageResponse)

    await expect(apiClient.request('api/json')).resolves.toEqual({
      id: 'campaign-1'
    })
    await expect(apiClient.request('api/text')).resolves.toBe('ready')
    await expect(apiClient.request('api/image')).resolves.toBe(imageBlob)
  })

  it('returns blob metadata without forwarding internal options to fetch', async () => {
    const fileBlob = new Blob(['export'])
    const response = mockResponse({
      status: 201,
      statusText: 'Created',
      contentType: 'application/octet-stream',
      blob: fileBlob
    })
    response.headers.set('content-disposition', 'attachment; filename=export.zip')
    fetch.mockResolvedValue(response)

    await expect(
      apiClient.request('api/export', {
        responseType: 'blob',
        suppressAuthRedirect: true
      })
    ).resolves.toEqual({
      data: fileBlob,
      headers: {
        'content-disposition': 'attachment; filename=export.zip',
        'content-type': 'application/octet-stream'
      },
      status: 201,
      statusText: 'Created'
    })

    const [, requestOptions] = fetch.mock.calls[0]
    expect(requestOptions).not.toHaveProperty('responseType')
    expect(requestOptions).not.toHaveProperty('suppressAuthRedirect')
  })

  it('formats FastAPI validation errors into a readable message', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        status: 422,
        statusText: 'Unprocessable Entity',
        json: {
          detail: [
            { loc: ['body', 'url'], msg: 'Invalid URL' },
            { loc: ['body', 'name'], msg: 'Required' }
          ]
        }
      })
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await expect(apiClient.request('api/campaigns')).rejects.toThrow(
      'url: Invalid URL; name: Required'
    )
  })

  it('uses a status fallback when an error response has no JSON body', async () => {
    const response = mockResponse({
      status: 503,
      statusText: 'Service Unavailable'
    })
    response.json.mockRejectedValue(new SyntaxError('empty response'))
    fetch.mockResolvedValue(response)
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await expect(apiClient.request('api/status')).rejects.toThrow(
      'HTTP error! status: 503'
    )
  })

  it('clears the session and redirects after an unauthorized response', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        status: 401,
        statusText: 'Unauthorized',
        json: { detail: 'Session expired' }
      })
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await expect(apiClient.request('api/private')).rejects.toThrow(
      'Session expired'
    )

    expect(mocks.authStore.logout).toHaveBeenCalledOnce()
    expect(mocks.router.push).toHaveBeenCalledWith('/login')
  })

  it('can suppress only the redirect while still clearing an invalid session', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        status: 401,
        statusText: 'Unauthorized',
        json: { detail: 'Not authenticated' }
      })
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await expect(
      apiClient.request('api/auth/me', { suppressAuthRedirect: true })
    ).rejects.toThrow('Not authenticated')

    expect(mocks.authStore.logout).toHaveBeenCalledOnce()
    expect(mocks.router.push).not.toHaveBeenCalled()
  })

  it('rethrows aborted requests without logging them as fetch errors', async () => {
    const abortError = new DOMException('Aborted', 'AbortError')
    fetch.mockRejectedValue(abortError)
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {})

    await expect(
      apiClient.request('api/poll', {
        signal: new AbortController().signal
      })
    ).rejects.toBe(abortError)

    expect(consoleError).not.toHaveBeenCalled()
  })
})
