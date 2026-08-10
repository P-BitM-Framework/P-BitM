<script setup>
import { ref, watch } from 'vue'
import { backendService } from '@/services/backend'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import jszip from 'jszip'

const props = defineProps({
    victim: Object,
    campaign: Object
})

const toast = useToast()
const files = ref([])
const loading = ref(false)

const fetchFiles = async () => {
    if (!props.victim || !props.campaign) return

    loading.value = true
    try {
        const response = await backendService.getFilesHijacked(props.campaign.id, props.victim.id)
        files.value = response.map((fileMeta) => ({
            id: fileMeta.id,
            filename: fileMeta.name,
            size_bytes: fileMeta.size_bytes || 0,
            size_mb: fileMeta.size_mb,
            collected_at: fileMeta.collected_at,
            download_url: fileMeta.download_url
        }))
    } catch (error) {
        console.error('Failed to fetch files:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to load hijacked files',
            life: 3000
        })
        files.value = []
    } finally {
        loading.value = false
    }
}

const saveBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
}

const downloadFile = async (file) => {
    if (!file?.download_url) return
    try {
        const response = await backendService.getFileBlob(file.download_url)
        saveBlob(response.data, file.filename)
        toast.add({
            severity: 'success',
            summary: 'Downloaded',
            detail: `${file.filename} downloaded`,
            life: 2000
        })
    } catch (error) {
        console.error('Download error:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to download file',
            life: 3000
        })
    }
}

const downloadAllFiles = async () => {
    if (!files.value || files.value.length === 0) return

    try {
        const zip = new jszip()
        const blobs = await Promise.all(
            files.value.map(async (file) => ({
                file,
                blob: (await backendService.getFileBlob(file.download_url)).data
            }))
        )
        blobs.forEach(({ file, blob }) => zip.file(file.filename, blob))
        const content = await zip.generateAsync({ type: 'blob' })
        saveBlob(content, `hijacked_files_${props.victim.id}.zip`)
        toast.add({
            severity: 'success',
            summary: 'Downloaded',
            detail: `${files.value.length} files downloaded`,
            life: 2000
        })
    } catch (error) {
        console.error('Error generating zip:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to create zip file',
            life: 3000
        })
    }
}

watch(
    () => props.victim,
    async (newVictim) => {
        if (newVictim) {
            await fetchFiles()
        }
    },
    { immediate: true }
)

</script>
<template>
    <div class="hijacked-files-panel">
        <div class="panel-header">
            <h4>Hijacked Files</h4>
            <div class="header-actions">
                <Button
                    icon="pi pi-refresh"
                    size="small"
                    text
                    @click="fetchFiles"
                />
                <Button
                    icon="pi pi-download"
                    label="Download All"
                    size="small"
                    :disabled="!files || files.length === 0"
                    @click="downloadAllFiles"
                />
            </div>
        </div>

        <div v-if="loading" class="loading-state">
            <i class="pi pi-spin pi-spinner"></i>
            <span>Loading files...</span>
        </div>

        <div v-else-if="files && files.length > 0" class="files-table">
            <DataTable
                :value="files"
                stripedRows
                :rows="10"
                :paginator="files.length > 10"
                class="data-table"
            >
                <Column field="filename" header="Filename" sortable>
                    <template #body="slotProps">
                        <div class="filename-cell">
                            <i class="pi pi-file"></i>
                            <span>{{ slotProps.data.filename }}</span>
                        </div>
                    </template>
                </Column>

                <Column field="size_mb" header="Size" sortable>
                    <template #body="slotProps">
                        <Tag :value="`${slotProps.data.size_mb} MB`" severity="info" />
                    </template>
                </Column>

                <Column field="collected_at" header="Collected" sortable>
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.collected_at).toLocaleString() }}
                    </template>
                </Column>

                <Column header="Actions">
                    <template #body="slotProps">
                        <Button
                            icon="pi pi-download"
                            size="small"
                            text
                            @click="downloadFile(slotProps.data)"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>

        <div v-else class="empty-state">
            <i class="pi pi-inbox"></i>
            <p>No hijacked files yet</p>
        </div>
    </div>
</template>

<style scoped>
.hijacked-files-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.panel-header h4 {
    margin: 0;
    color: var(--color-heading);
    font-size: 1.125rem;
}

.header-actions {
    display: flex;
    gap: 0.5rem;
}

.loading-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--color-text-mute);
}

.files-table {
    background: var(--color-background);
    border-radius: 8px;
    overflow: hidden;
}

.filename-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.filename-cell i {
    color: var(--primary-color);
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: var(--color-text-mute);
}

.empty-state i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
    font-size: 1rem;
}
</style>
