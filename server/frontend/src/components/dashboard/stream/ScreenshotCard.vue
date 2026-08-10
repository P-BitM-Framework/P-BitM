<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import { useToast } from 'primevue/usetoast'
import jszip from 'jszip'
import { formatDateLocal } from '@/utils/utils'

const props = defineProps({
    campaignId: {
        type: String,
        required: true
    },
    victimId: {
        type: String,
        required: true
    },
    screenshots: {
        type: Array,
        required: true
    },
    loading: {
        type: Boolean,
        default: false
    },
    capturePending: {
        type: Boolean,
        default: false
    },
    canCapture: {
        type: Boolean,
        default: false
    },
    lastUpdated: {
        type: [Date, String],
        default: null
    }
})

const emit = defineEmits(['refresh', 'capture'])
const toast = useToast()

const view = ref('grid') // 'grid' | 'list'
const lightboxVisible = ref(false)
const currentIndex = ref(0)
const zoomLevel = ref(1)
const searchQuery = ref('')

const currentScreenshot = computed(() => props.screenshots[currentIndex.value])

const filteredScreenshots = computed(() => {
    if (!searchQuery.value) return props.screenshots

    const query = searchQuery.value.toLowerCase()
    return props.screenshots.filter(s =>
        s.alt?.toLowerCase().includes(query) ||
        s.timestamp?.toLowerCase().includes(query)
    )
})

const lastFetchTime = computed(() => {
    if (!props.lastUpdated) return null
    return new Date(props.lastUpdated).toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    })
})

function openLightbox(screenshot) {
    const index = props.screenshots.findIndex(item => item.id === screenshot.id)
    if (index < 0) return
    currentIndex.value = index
    zoomLevel.value = 1
    lightboxVisible.value = true
}

function nextScreenshot() {
    if (currentIndex.value < props.screenshots.length - 1) {
        currentIndex.value++
        zoomLevel.value = 1
    }
}

function previousScreenshot() {
    if (currentIndex.value > 0) {
        currentIndex.value--
        zoomLevel.value = 1
    }
}

function zoomIn() {
    zoomLevel.value = Math.min(zoomLevel.value + 0.25, 3)
}

function zoomOut() {
    zoomLevel.value = Math.max(zoomLevel.value - 0.25, 0.5)
}

function downloadCurrent() {
    if (!currentScreenshot.value) return
    downloadScreenshot(currentScreenshot.value)
}

function downloadScreenshot(screenshot) {
    const link = document.createElement('a')
    link.href = screenshot.itemImageSrc
    link.download = `screenshot_${screenshot.id}_${Date.now()}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.add({
        severity: 'success',
        summary: 'Download',
        detail: 'Screenshot downloaded',
        life: 2000
    })
}

async function downloadAll() {
    if (!props.campaignId || props.screenshots.length === 0) return

    try {
        toast.add({
            severity: 'info',
            summary: 'Preparing Download',
            detail: 'Creating ZIP archive...',
            life: 3000
        })

        const zip = new jszip()
        props.screenshots.forEach((screenshot, index) => {
            const filename = `screenshot_${screenshot.id || index + 1}.png`
            zip.file(filename, screenshot.blob)
        })

        const content = await zip.generateAsync({ type: 'blob' })
        const downloadUrl = URL.createObjectURL(content)
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = `screenshots_${props.victimId}_${Date.now()}.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(downloadUrl)

        toast.add({
            severity: 'success',
            summary: 'Download Complete',
            detail: `${props.screenshots.length} screenshots downloaded`,
            life: 3000
        })
    } catch (error) {
        console.error('❌ Error generating zip:', error)
        toast.add({
            severity: 'error',
            summary: 'Download Failed',
            detail: 'Failed to create ZIP archive',
            life: 3000
        })
    }
}

function formatTime(timestamp) {
    if (!timestamp) return 'N/A'

    return formatDateLocal(timestamp)
}

function formatSize(bytes) {
    if (!bytes) return 'N/A'
    return `${(bytes / 1024).toFixed(0)} KB`
}

// Keyboard navigation
function handleKeydown(e) {
    if (!lightboxVisible.value) return

    if (e.key === 'ArrowLeft') previousScreenshot()
    if (e.key === 'ArrowRight') nextScreenshot()
    if (e.key === 'Escape') lightboxVisible.value = false
}

onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
    <div class="screenshot-card">
        <!-- Header -->
        <div class="card-header">
            <div class="header-left">
                <h4>📸 Screenshots ({{ props.screenshots.length }})</h4>
                <span v-if="lastFetchTime" class="last-update">
                    Updated: {{ lastFetchTime }}
                </span>
            </div>

            <div class="header-actions">
                <Button
                    label="Capture"
                    icon="pi pi-camera"
                    size="small"
                    :loading="capturePending"
                    :disabled="!canCapture"
                    @click="emit('capture')"
                />
                <Button
                    label="Refresh"
                    icon="pi pi-refresh"
                    size="small"
                    outlined
                    :loading="loading"
                    @click="emit('refresh')"
                />
                <IconField iconPosition="left">
                    <InputIcon>
                        <i class="pi pi-search" />
                    </InputIcon>
                    <InputText
                        v-model="searchQuery"
                        placeholder="Search screenshot..."
                    />
                </IconField>

                <div class="view-toggle">
                    <Button
                        icon="pi pi-th-large"
                        :text="view !== 'grid'"
                        :outlined="view === 'grid'"
                        size="small"
                        rounded
                        @click="view = 'grid'"
                        v-tooltip.bottom="'Grid View'"
                    />
                    <Button
                        icon="pi pi-list"
                        :text="view !== 'list'"
                        :outlined="view === 'list'"
                        size="small"
                        rounded
                        @click="view = 'list'"
                        v-tooltip.bottom="'List View'"
                    />
                </div>

                <Button
                    label="Download All"
                    icon="pi pi-download"
                    size="small"
                    :disabled="props.screenshots.length === 0"
                    @click="downloadAll"
                />
            </div>
        </div>

        <!-- Empty State -->
        <div v-if="props.screenshots.length === 0" class="empty-state">
            <i class="pi pi-images"></i>
            <p>No screenshots captured yet</p>
            <small>Capture one while the victim browser is connected.</small>
        </div>

        <!-- Grid View -->
        <div v-else-if="view === 'grid'" class="gallery-grid">
            <div
                v-for="screenshot in filteredScreenshots"
                :key="screenshot.id"
                class="gallery-item"
                @click="openLightbox(screenshot)"
            >
                <img :src="screenshot.thumbnail" :alt="screenshot.alt" />
                <div class="item-overlay">
                    <span class="timestamp">{{ formatTime(screenshot.timestamp) }}</span>
                    <div class="item-actions">
                        <Button
                            icon="pi pi-search-plus"
                            rounded
                            text
                            size="small"
                            @click.stop="openLightbox(screenshot)"
                        />
                        <Button
                            icon="pi pi-download"
                            rounded
                            text
                            size="small"
                            @click.stop="downloadScreenshot(screenshot)"
                        />
                    </div>
                </div>
            </div>
        </div>

        <!-- List View -->
        <div v-else class="gallery-list">
            <div
                v-for="screenshot in filteredScreenshots"
                :key="screenshot.id"
                class="list-item"
            >
                <div class="list-item-thumbnail">
                    <img
                        :src="screenshot.thumbnail"
                        :alt="screenshot.alt"
                        @click="openLightbox(screenshot)"
                    />
                </div>

                <div class="list-item-info">
                    <div class="info-header">
                        <span class="info-name">{{ screenshot.alt }}</span>
                        <span class="info-time">{{ formatTime(screenshot.timestamp) }}</span>
                    </div>
                    <div class="info-details">
                        <span class="info-url">{{ screenshot.alt }}</span>
                        <span class="info-meta">{{ screenshot.resolution }} • {{ formatSize(screenshot.size) }}</span>
                    </div>
                </div>

                <div class="list-item-actions">
                    <Button
                        icon="pi pi-search-plus"
                        size="small"
                        text
                        rounded
                        @click="openLightbox(screenshot)"
                        v-tooltip.bottom="'View Full Size'"
                    />
                    <Button
                        icon="pi pi-download"
                        size="small"
                        text
                        rounded
                        @click="downloadScreenshot(screenshot)"
                        v-tooltip.bottom="'Download'"
                    />
                </div>
            </div>
        </div>

        <!-- Lightbox Dialog -->
        <Dialog
            v-model:visible="lightboxVisible"
            modal
            :draggable="false"
            :dismissableMask="true"
            :closable="false"
            :style="{ width: '90vw', maxWidth: '1600px' }"
            class="screenshot-lightbox"
        >
            <template #header>
                <div class="lightbox-header">
                    <span class="lightbox-title">
                        Screenshot {{ currentIndex + 1 }} of {{ props.screenshots.length }}
                    </span>
                    <div class="lightbox-actions">
                        <Button
                            icon="pi pi-search-plus"
                            text
                            rounded
                            @click="zoomIn"
                            v-tooltip.bottom="'Zoom In'"
                        />
                        <Button
                            icon="pi pi-search-minus"
                            text
                            rounded
                            @click="zoomOut"
                            v-tooltip.bottom="'Zoom Out'"
                        />
                        <Button
                            icon="pi pi-download"
                            text
                            rounded
                            @click="downloadCurrent"
                            v-tooltip.bottom="'Download'"
                        />
                        <Button
                            icon="pi pi-times"
                            text
                            rounded
                            @click="lightboxVisible = false"
                            v-tooltip.bottom="'Close (ESC)'"
                        />
                    </div>
                </div>
            </template>

            <div class="lightbox-content">
                <Button
                    icon="pi pi-chevron-left"
                    text
                    rounded
                    size="large"
                    class="nav-btn nav-prev"
                    @click="previousScreenshot"
                    :disabled="currentIndex === 0"
                />

                <div class="screenshot-container" :style="{ transform: `scale(${zoomLevel})` }">
                    <img :src="currentScreenshot?.full_size" alt="Full size screenshot" />
                </div>

                <Button
                    icon="pi pi-chevron-right"
                    text
                    rounded
                    size="large"
                    class="nav-btn nav-next"
                    @click="nextScreenshot"
                    :disabled="currentIndex === screenshots.length - 1"
                />
            </div>

            <template #footer>
                <div class="lightbox-footer">
                    <div class="screenshot-info">
                        <span>{{ formatTime(currentScreenshot?.timestamp) }}</span>
                        <span>•</span>
                        <span>{{ currentScreenshot?.url }}</span>
                        <span>•</span>
                        <span>{{ currentScreenshot?.resolution }}</span>
                        <span>•</span>
                        <span>{{ formatSize(currentScreenshot?.size) }}</span>
                    </div>
                    <div class="navigation-hint">
                        <kbd>←</kbd> Previous  •  <kbd>→</kbd> Next  •  <kbd>ESC</kbd> Close
                    </div>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.screenshot-card {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding: 10px;
    height: 100%;
    width: 100%;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    flex-shrink: 0;
    width: 100%;
}

.view-toggle {
    display: flex;
    gap: 0.25rem;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.header-left h4 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
    margin: 0;
}

.last-update {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

.header-actions {
    display: flex;
    gap: 0.75rem;
    align-items: center;
}

/* Empty State */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 4rem 2rem;
    color: var(--color-text-mute);
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    width: 100%;
    box-sizing: border-box;
}

.empty-state i {
    font-size: 3rem;
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
    font-size: 1rem;
    font-weight: 500;
}

.empty-state small {
    font-size: 0.8rem;
    opacity: 0.7;
}

/* Grid View */
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
    max-height: 600px;
    overflow-y: auto;
    padding-right: 0.5rem;
    width: 100%;
    box-sizing: border-box;
}

/* Scrollbar styling */
.gallery-grid::-webkit-scrollbar,
.gallery-list::-webkit-scrollbar {
    width: 8px;
}

.gallery-grid::-webkit-scrollbar-track,
.gallery-list::-webkit-scrollbar-track {
    background: var(--color-background-mute);
    border-radius: 4px;
}

.gallery-grid::-webkit-scrollbar-thumb,
.gallery-list::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
}

.gallery-grid::-webkit-scrollbar-thumb:hover,
.gallery-list::-webkit-scrollbar-thumb:hover {
    background: var(--color-border-hover);
}

.gallery-item {
    position: relative;
    aspect-ratio: 4 / 3;
    border-radius: 6px;
    overflow: hidden;
    cursor: pointer;
    border: 1px solid var(--color-border);
    transition: transform 0.2s;
    width: 100%;
}

.gallery-item:hover {
    transform: scale(1.02);
    border-color: var(--color-border-hover);
}

.gallery-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.item-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 50%);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 0.75rem;
    opacity: 0;
    transition: opacity 0.2s;
}

.gallery-item:hover .item-overlay {
    opacity: 1;
}

.timestamp {
    font-size: 0.75rem;
    color: white;
    font-weight: 500;
    align-self: flex-start;
    background-color: rgba(0,0,0,0.6);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
}

.item-actions {
    display: flex;
    gap: 0.5rem;
    align-self: flex-end;
}

/* List View */
.gallery-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-height: 600px;
    overflow-y: auto;
    padding-right: 0.5rem;
    width: 100%;
    box-sizing: border-box;
}

.list-item {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 1rem 1.25rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    transition: border-color 0.2s;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
}

.list-item:hover {
    border-color: var(--color-border-hover);
}

.list-item-thumbnail {
    flex-shrink: 0;
    width: 140px;
    height: 105px;
    border-radius: 4px;
    overflow: hidden;
    cursor: pointer;
    border: 1px solid var(--color-border);
}

.list-item-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.2s;
}

.list-item-thumbnail:hover img {
    transform: scale(1.05);
}

.list-item-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-width: 0;
    overflow: hidden;
}

.info-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.info-name {
    font-weight: 600;
    color: var(--color-heading);
    font-size: 0.875rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.info-time {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    flex-shrink: 0;
}

.info-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.info-url {
    font-size: 0.75rem;
    color: var(--color-text-mute);
    font-family: 'JetBrains Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.info-meta {
    font-size: 0.7rem;
    color: var(--color-text-mute);
    opacity: 0.7;
}

.list-item-actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
    margin-left: auto;
}

/* Lightbox */
.screenshot-lightbox :deep(.p-dialog-content) {
    padding: 0;
    background-color: #000;
}

.lightbox-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0 1rem;
}

.lightbox-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-heading);
}

.lightbox-actions {
    display: flex;
    gap: 0.5rem;
}

.lightbox-content {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    background-color: #000;
}

.screenshot-container {
    max-width: 100%;
    max-height: 70vh;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.3s ease;
}

.screenshot-container img {
    max-width: 100%;
    max-height: 70vh;
    object-fit: contain;
}

.nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background-color: rgba(0, 0, 0, 0.5) !important;
    color: white !important;
}

.nav-prev {
    left: 1rem;
}

.nav-next {
    right: 1rem;
}

.nav-btn:hover {
    background-color: rgba(0, 0, 0, 0.8) !important;
}

.lightbox-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 1rem;
}

.screenshot-info {
    display: flex;
    gap: 0.75rem;
    font-size: 0.875rem;
    color: var(--color-text-mute);
}

.navigation-hint {
    font-size: 0.75rem;
    color: var(--color-text-mute);
}

.navigation-hint kbd {
    padding: 0.125rem 0.375rem;
    background-color: var(--color-background-mute);
    border: 1px solid var(--color-border);
    border-radius: 3px;
    font-family: monospace;
    font-size: 0.7rem;
}

/* Responsive */
@media (max-width: 768px) {
    .card-header {
        flex-direction: column;
        align-items: stretch;
    }

    .header-actions {
        flex-wrap: wrap;
    }

    .gallery-grid {
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }

    .list-item {
        flex-direction: column;
        align-items: stretch;
    }

    .list-item-thumbnail {
        width: 100%;
        height: 150px;
    }

    .list-item-actions {
        justify-content: flex-end;
        margin-left: 0;
    }

    .screenshot-container img {
        max-height: 50vh;
    }
}
</style>
