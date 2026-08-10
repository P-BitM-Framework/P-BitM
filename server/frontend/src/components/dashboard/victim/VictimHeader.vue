<script setup>
import { computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import { formatTimeAgo } from '@/utils/utils.js'

// Brand logos (Iconify, bundled at build time via unplugin-icons — no runtime CDN calls).
// "unknown" has no brand logo, so it falls back to a PrimeIcons glyph (pi-globe/pi-desktop)
// instead, matching the icon set already used everywhere else in this app.
import ChromeIcon from 'virtual:icons/logos/chrome'
import FirefoxIcon from 'virtual:icons/logos/firefox'
import SafariIcon from 'virtual:icons/logos/safari'
import EdgeIcon from 'virtual:icons/logos/microsoft-edge'
import OperaIcon from 'virtual:icons/logos/opera'

import WindowsIcon from 'virtual:icons/logos/microsoft-windows-icon'
import MacosIcon from 'virtual:icons/logos/apple'
import LinuxIcon from 'virtual:icons/logos/linux-tux'
import AndroidIcon from 'virtual:icons/logos/android-icon'

// Maps (stessi)
const browserIconMap = {
    'chrome': ChromeIcon, 'firefox': FirefoxIcon,
    'safari': SafariIcon, 'edge': EdgeIcon,
    'opera': OperaIcon
}

const osIconMap = {
    'windows': WindowsIcon, 'macos': MacosIcon,
    'linux': LinuxIcon, 'android': AndroidIcon
}

const props = defineProps({ victim: Object, campaign: Object })
const emit = defineEmits(['back', 'export', 'kill'])
const toast = useToast()

const statusConfig = computed(() => {
    const isLive = props.victim.is_active

    return {
        severity: isLive ? 'success' : 'secondary',
        icon: isLive ? 'pi pi-circle-fill' : 'pi pi-circle',
        label: isLive ? 'LIVE' : 'OFFLINE'
    }
})

const lastSeen = computed(() => formatTimeAgo(props.victim.last_seen))

// Browser/OS parsers (ottimizzati)
const browserInfo = computed(() => {
    const ua = props.victim.browser || ''
    if (!ua) return { name: 'Unknown', icon: 'unknown' }

    const uaLower = ua.toLowerCase()
    if (uaLower.includes('firefox')) return { name: 'Firefox', icon: 'firefox' }
    if (uaLower.includes('chrome') && !uaLower.includes('chromium')) return { name: 'Chrome', icon: 'chrome' }
    if (uaLower.includes('safari') && !uaLower.includes('chrome')) return { name: 'Safari', icon: 'safari' }
    if (uaLower.includes('edge')) return { name: 'Edge', icon: 'edge' }
    if (uaLower.includes('opera')) return { name: 'Opera', icon: 'opera' }
    return { name: 'Other', icon: 'unknown' }
})

const osInfo = computed(() => {
    const platform = props.victim.os || ''
    if (!platform) return { name: 'Unknown', icon: 'unknown' }

    const platformLower = platform.toLowerCase()
    if (platformLower.includes('windows')) return { name: 'Windows', icon: 'windows' }
    if (platformLower.includes('mac')) return { name: 'macOS', icon: 'macos' }
    if (platformLower.includes('linux')) return { name: 'Linux', icon: 'linux' }
    if (platformLower.includes('iphone') || platformLower.includes('ios')) return { name: 'iOS', icon: 'macos' }
    if (platformLower.includes('android')) return { name: 'Android', icon: 'android' }
    return { name: 'Unknown', icon: 'unknown' }
})

const getBrowserIconComponent = computed(() => browserIconMap[browserInfo.value.icon] || null)
const getOsIconComponent = computed(() => osIconMap[osInfo.value.icon] || null)

const isStandalone = computed(() => props.campaign?.campaign_type === 'standalone')

const trackingUrl = computed(() => {
    if (!props.campaign?.public_url || !props.victim?.tracking_id) return ''
    const base = props.campaign.public_url.endsWith('/')
        ? props.campaign.public_url
        : `${props.campaign.public_url}/`
    const routes = props.campaign?.advanced_options?.routes || {}
    const entryPath = props.campaign?.advanced_options?.routes
        ? (routes.entry_path || '')
        : 'continue'
    const cleanUrl = entryPath
        ? `${base}${entryPath}`
        : base.replace(/\/$/, '')
    if (routes.tracking_parameter) {
        const url = new URL(cleanUrl)
        url.searchParams.set(routes.tracking_parameter, props.victim.tracking_id)
        return url.toString()
    }
    return `${cleanUrl}/${props.victim.tracking_id}`
})

const copyTrackingUrl = async () => {
    if (!trackingUrl.value) return
    try {
        await navigator.clipboard.writeText(trackingUrl.value)
        toast.add({
            severity: 'success',
            summary: 'Copied',
            detail: 'Phishing URL copied to clipboard',
            life: 2000
        })
    } catch (_error) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to copy phishing URL',
            life: 3000
        })
    }
}
</script>

<template>
    <div class="victim-header">
        <div class="header-left">
            <Button
                icon="pi pi-arrow-left"
                text rounded
                @click="emit('back')"
                class="back-btn"
                severity="secondary"
            />

            <div class="victim-identity">
                <!-- Status + Last Seen (no icons) -->
                <div class="status-row">
                    <Tag
                        :value="statusConfig.label"
                        :severity="statusConfig.severity"
                        :icon="statusConfig.icon"
                        size="small"
                        class="status-tag"
                    />
                    <span class="last-seen">{{ lastSeen }}</span>
                </div>

                <!-- Divider -->
                <div class="divider"></div>

                <!-- Name + Email + IP (stacked) -->
                <div class="victim-info-section">
                    <div class="name-email-section">
                        <span class="victim-name" v-if="victim.first_name || victim.last_name">
                            {{ victim.first_name || '' }} {{ victim.last_name || '' }}
                        </span>
                        <code class="victim-email">✉️ {{ victim.email || 'Anonymous' }}</code>
                    </div>

                    <!-- IP + Device Icons insieme -->
                    <div class="ip-devices-row">
                        <span class="victim-ip">📍 {{ victim.ip_address || 'Unknown IP' }}</span>
                    </div>
                    <div class="device-icons-compact">
                        <component v-if="getOsIconComponent" :is="getOsIconComponent" class="device-icon"
                            :title="osInfo.name" role="img" :aria-label="osInfo.name" />
                        <i v-else class="pi pi-desktop device-icon" :title="osInfo.name" :aria-label="osInfo.name" />
                        <component v-if="getBrowserIconComponent" :is="getBrowserIconComponent" class="device-icon"
                            :title="browserInfo.name" role="img" :aria-label="browserInfo.name" />
                        <i v-else class="pi pi-globe device-icon" :title="browserInfo.name" :aria-label="browserInfo.name" />
                    </div>
                </div>
            </div>
        </div>

        <!-- Export Button (top right) -->
        <div class="header-actions">
            <div v-if="isStandalone" class="tracking-url">
                <span class="tracking-label">🎣 Phishing URL 🎣</span>
                <div class="tracking-input">
                    <InputText :modelValue="trackingUrl" readonly />
                    <Button
                        icon="pi pi-copy"
                        severity="secondary"
                        text
                        @click="copyTrackingUrl"
                        v-tooltip.bottom="'Copy URL'"
                    />
                </div>
            </div>
            <Button
                label="Export"
                icon="pi pi-download"
                outlined
                size="small"
                @click="emit('export')"
                class="action-btn"
            />
        </div>
    </div>
</template>

<style scoped>
.victim-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.5rem;
    padding: 1rem 1.5rem;
    background: var(--color-background-soft);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    transition: var(--transition-interactive);
}

.header-left {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    flex: 1;
    min-width: 0;
}

.back-btn {
    flex-shrink: 0;
    color: var(--color-text-mute);
    padding: 0.5rem;
    border-radius: 8px;
    transition: var(--transition-interactive);
    margin-top: 0.25rem;
}

.back-btn:hover {
    background: var(--color-background);
    color: var(--color-text);
    transform: translateX(-2px);
}

.victim-identity {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    min-width: 0;
}

/* Status Row - no icons */
.status-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.status-tag {
    font-weight: 600 !important;
    padding: 0.3rem 0.75rem !important;
    font-size: 0.7rem !important;
    white-space: nowrap;
}

.last-seen {
    color: var(--color-text-mute);
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
}

.last-seen::before {
    content: '🕐 ';
}

/* Divider */
.divider {
    height: 1px;
    background: var(--color-border);
    opacity: 0.5;
}

/* Victim Info Section */
.victim-info-section {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.name-email-section {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.victim-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-heading);
    line-height: 1.2;
}

.victim-email {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text);
    font-family: 'Courier New', monospace;
}

/* IP + Device Icons */
.ip-devices-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.victim-ip {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text);
    font-family: 'Courier New', monospace;
    white-space: nowrap;
}

/* Device Icons Compact */
.device-icons-compact {
    display: flex;
    gap: 0.4rem;
    align-items: center;
}

.device-icon {
    width: 18px;
    height: 18px;
    font-size: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    object-fit: contain;
    flex-shrink: 0;
    opacity: 0.75;
    transition: opacity 0.2s;
}

.device-icon:hover {
    opacity: 1;
}

/* Actions */
.header-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    flex-shrink: 0;
}

.tracking-url {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.75rem;
    background: var(--color-background);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    min-width: 320px;
}

.tracking-label {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.tracking-input {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.tracking-input :deep(.p-inputtext) {
    flex: 1;
}

.action-btn {
    min-width: auto;
    padding: 0.5rem 1rem;
}

/* Responsive */
@media (max-width: 1024px) {
    .victim-header {
        padding: 0.875rem 1.25rem;
    }

    .device-icons-compact {
        gap: 0.3rem;
    }

    .device-icon {
        width: 16px;
        height: 16px;
        font-size: 16px;
    }
}

@media (max-width: 768px) {
    .victim-header {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
        padding: 1rem;
    }

    .header-left {
        width: 100%;
        align-items: flex-start;
    }

    .status-row {
        width: 100%;
    }

    .ip-devices-row {
        width: 100%;
    }

    .header-actions {
        width: 100%;
    }

    .action-btn {
        flex: 1;
    }

    .tracking-url {
        min-width: unset;
    }
}

@media (max-width: 480px) {
    .victim-header {
        padding: 0.75rem;
    }

    .victim-name {
        font-size: 0.9rem;
    }

    .status-row {
        gap: 0.5rem;
    }

    .device-icons-compact {
        gap: 0.25rem;
    }

    .device-icon {
        width: 15px;
        height: 15px;
        font-size: 15px;
    }

    .ip-devices-row {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25rem;
    }
}
</style>
