/**
 * Format a timestamp as a relative "time ago" string.
 * @param {string|Date} timestamp - ISO string from the backend (UTC)
 * @returns {string} e.g. "5m ago", "2h ago"
 */
export function formatTimeAgo(timestamp) {
  if (!timestamp) return 'N/A'

  try {
    let input = timestamp

    // Backend timestamps without an explicit timezone are UTC.
    if (typeof input === 'string' && !input.endsWith('Z') && !input.includes('+')) {
      input = input + 'Z'
    }

    const then = new Date(input)
    const now = new Date()

    if (isNaN(then.getTime())) {
      console.warn('Invalid timestamp:', timestamp)
      return 'Invalid'
    }

    const diffMs = now - then
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSeconds < 10) return 'Just now'
    if (diffSeconds < 60) return `${diffSeconds}s ago`
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
    return `${Math.floor(diffDays / 365)}y ago`

  } catch (error) {
    console.error('formatTimeAgo error:', error, timestamp)
    return 'N/A'
  }
}

export function formatDateLocal(timestamp, includeSeconds = false) {
  if (!timestamp) return 'N/A'

  try {
    // Backend timestamps without an explicit timezone are UTC.
    if (typeof timestamp === 'string' && !timestamp.endsWith('Z') && !timestamp.includes('+')) {
      timestamp = timestamp + 'Z'
    }

    const date = new Date(timestamp)

    if (isNaN(date.getTime())) {
      console.warn('Invalid date:', timestamp)
      return 'Invalid'
    }

    const options = {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }

    if (includeSeconds) {
      options.second = '2-digit'
    }

    return date.toLocaleString('en-GB', options)

  } catch (error) {
    console.error('formatDateLocal error:', error, timestamp)
    return 'N/A'
  }
}

/**
 * Format only the date portion, in the local timezone.
 * @param {string|Date} timestamp - ISO string from the backend (UTC)
 * @returns {string} e.g. "Feb 5, 2026"
 */
export function formatDateOnly(timestamp) {
  if (!timestamp) return 'N/A'

  try {
    const date = new Date(timestamp)

    if (isNaN(date.getTime())) {
      console.warn('Invalid date:', timestamp)
      return 'Invalid'
    }

    const year = date.getFullYear()
    const currentYear = new Date().getFullYear()

    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: year !== currentYear ? 'numeric' : undefined
    })

  } catch (error) {
    console.error('formatDateOnly error:', error, timestamp)
    return 'N/A'
  }
}

/**
 * Format only the time portion, in the local timezone.
 * @param {string|Date} timestamp - ISO string from the backend (UTC)
 * @returns {string} e.g. "2:20 PM"
 */
export function formatTimeOnly(timestamp) {
  if (!timestamp) return 'N/A'

  try {
    const date = new Date(timestamp)

    if (isNaN(date.getTime())) {
      console.warn('Invalid time:', timestamp)
      return 'Invalid'
    }

    return date.toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })

  } catch (error) {
    console.error('formatTimeOnly error:', error, timestamp)
    return 'N/A'
  }
}

export function getVictimStatus(lastSeenTimestamp) {
  if (!lastSeenTimestamp) {
    return { isLive: false, label: 'Never', severity: 'danger' }
  }

  try {
    const lastSeen = new Date(lastSeenTimestamp)
    const now = new Date()

    if (isNaN(lastSeen.getTime())) {
      return { isLive: false, label: 'Invalid', severity: 'secondary' }
    }

    const diffMs = now - lastSeen
    const diffMinutes = Math.floor(diffMs / 60000)
    const isLive = diffMs < 300000 // 5 minutes

    return {
      isLive,
      label: isLive ? 'LIVE' : `${diffMinutes}m ago`,
      severity: isLive ? 'success' : 'warning'
    }

  } catch (error) {
    console.error('getVictimStatus error:', error, lastSeenTimestamp)
    return { isLive: false, label: 'Error', severity: 'danger' }
  }
}

const CAMPAIGN_STATUS_CONFIGS = {
  draft: { severity: 'secondary', icon: 'pi pi-file-edit', label: 'Draft' },
  active: { severity: 'success', icon: 'pi pi-circle-fill', label: 'Active' },
  scheduled: { severity: 'warning', icon: 'pi pi-clock', label: 'Scheduled' },
  paused: { severity: 'warning', icon: 'pi pi-pause', label: 'Paused' },
  completed: { severity: 'secondary', icon: 'pi pi-check-circle', label: 'Completed' },
  error: { severity: 'danger', icon: 'pi pi-exclamation-triangle', label: 'Error' }
}

/**
 * Map a campaign status to its display config (severity/icon/label).
 * @param {string} status
 * @returns {{severity: string, icon: string, label: string}}
 */
export function getCampaignStatusConfig(status) {
  return CAMPAIGN_STATUS_CONFIGS[status] || CAMPAIGN_STATUS_CONFIGS.draft
}
