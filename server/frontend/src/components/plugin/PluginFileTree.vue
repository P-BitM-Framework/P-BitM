<template>
  <div class="sidebar-section">
    <div class="section-header">
      <h3>
        <i class="pi pi-folder-open"></i>
        Files
      </h3>
      <div class="section-actions">
        <Button
          icon="pi pi-upload"
          text
          rounded
          size="small"
          :disabled="loading"
          @click="$emit('upload-click')"
          v-tooltip.right="'Upload Files'"
        />
        <Button
          icon="pi pi-plus"
          text
          rounded
          size="small"
          :disabled="loading"
          @click="$emit('new-file-click')"
          v-tooltip.right="'New File'"
        />
      </div>
    </div>

    <div v-if="loading" class="files-loading" aria-busy="true" aria-live="polite">
      <ProgressSpinner v-if="showLoading" aria-label="Loading files" />
    </div>

    <TransitionGroup v-else-if="files.length > 0" tag="div" name="list-fade" class="files-list">
      <div
        v-for="file in files"
        :key="file.name"
        class="file-item"
        :class="{ active: currentFile?.name === file.name }"
        @click="$emit('open-file', file)"
      >
        <Icon :icon="getFileIcon(file.name)" />
        <span class="file-name">{{ file.name }}</span>
        <span v-if="isFileModified(file.name)" class="modified-indicator">●</span>
        <div class="file-actions" @click.stop>
          <Button
            icon="pi pi-download"
            text
            rounded
            size="small"
            @click="$emit('download-file', file)"
            v-tooltip.right="'Download'"
          />
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            size="small"
            @click="$emit('delete-file', file)"
            v-tooltip.right="'Delete'"
          />
        </div>
      </div>

    </TransitionGroup>

    <div v-else class="empty-files">
      <i class="pi pi-inbox"></i>
      <p>No files yet</p>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

defineProps({
  files: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  showLoading: { type: Boolean, default: false },
  currentFile: { type: Object, default: null },
  isFileModified: { type: Function, required: true },
  getFileIcon: { type: Function, required: true }
})

defineEmits(['open-file', 'download-file', 'delete-file', 'upload-click', 'new-file-click'])
</script>

<style scoped>
.sidebar-section {
  margin-bottom: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-heading);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-header h3 i {
  font-size: 0.875rem;
  color: var(--color-text-mute);
}

.section-actions {
  display: flex;
  gap: 0.25rem;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.files-loading {
  display: grid;
  min-height: 7rem;
  place-items: center;
}

.files-loading :deep(.p-progressspinner) {
  width: 2rem;
  height: 2rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: var(--transition-interactive);
  position: relative;
}

.file-item:hover {
  background-color: var(--color-background-mute);
}

.file-item.active {
  background-color: var(--primary-color);
  color: white;
}

.file-item i {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.modified-indicator {
  color: var(--primary-color);
  font-size: 1rem;
  line-height: 0;
  margin-left: auto;
  margin-right: 0.25rem;
  flex-shrink: 0;
}

.file-item.active .modified-indicator {
  color: white;
}

.file-actions {
  display: flex;
  gap: 0.25rem;
}

.empty-files {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: var(--color-text-mute);
  text-align: center;
}

.empty-files i {
  font-size: 2rem;
  opacity: 0.5;
}

.empty-files p {
  margin: 0;
  font-size: 0.875rem;
}
</style>
