import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const DEFAULT_HEADERS = {
  'Content-Type': 'application/json'
}

function buildErrorMessage(errorData, status) {
  const detail = errorData?.detail
  if (!Array.isArray(detail)) {
    return detail || `HTTP error! status: ${status}`
  }
  return detail
    .map((item) => {
      const location = Array.isArray(item?.loc)
        ? item.loc.filter((part) => part !== 'body').join('.')
        : ''
      return `${location ? `${location}: ` : ''}${item?.msg || 'Invalid value'}`
    })
    .join('; ')
}

/**
 * Create an HTTP client carrying auth/CSRF wiring and response parsing
 * shared by every resource-specific API client.
 */
export function createApiClient(baseUrl = import.meta.env.VITE_API_BASE_URL || `${location.protocol}//${location.host}/`) {
  async function request(endpoint, options = {}) {
    const {
      suppressAuthRedirect = false,
      responseType,
      ...requestOptions
    } = options
    const url = `${baseUrl}${endpoint}`
    const headers = { ...DEFAULT_HEADERS, ...requestOptions.headers }

    if (requestOptions.body instanceof FormData) {
      delete headers['Content-Type']
    }

    const authStore = useAuthStore()
    const method = (requestOptions.method || 'GET').toUpperCase()
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && authStore.csrfToken) {
      headers['X-CSRF-Token'] = authStore.csrfToken
    }

    try {
      const response = await fetch(url, {
        ...requestOptions,
        headers,
        credentials: 'include'
      })

      if (!response.ok) {
        if (response.status === 401) {
          authStore.logout()
          if (!suppressAuthRedirect) {
            router.push('/login')
          }
        }
        const errorData = await response.json().catch(() => null)
        throw new Error(buildErrorMessage(errorData, response.status))
      }

      if (responseType === 'blob') {
        const blob = await response.blob()
        return {
          data: blob,
          headers: Object.fromEntries(response.headers.entries()),
          status: response.status,
          statusText: response.statusText
        }
      }

      const contentType = response.headers.get('content-type')

      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      } else if (contentType && contentType.includes('image/')) {
        return await response.blob()
      } else if (contentType && contentType.includes('text/')) {
        return await response.text()
      }

      try {
        return await response.json()
      } catch {
        return await response.blob()
      }
    } catch (error) {
      if (error?.name !== 'AbortError') {
        console.error('Fetch error:', error)
      }
      throw error
    }
  }

  return { request }
}

export function downloadFile(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
