<template>
  <div class="editor-area">
    <div v-if="!loading && openTabs.length > 0" class="editor-tabs">
      <div
        v-for="tab in openTabs"
        :key="tab.name"
        class="tab"
        :class="{ active: currentFile?.name === tab.name }"
        @click="$emit('switch-tab', tab)"
      >
        <Icon :icon="getFileIcon(tab.name)" />
        <span>{{ tab.name }}</span>
        <span v-if="isFileModified(tab.name)" class="unsaved-indicator">●</span>
        <Button
          v-if="openTabs.length > 1"
          icon="pi pi-times"
          text
          rounded
          size="small"
          class="close-tab-btn"
          @click.stop="$emit('close-tab', tab)"
        />
      </div>
    </div>

    <Transition name="fade" mode="out-in">
    <div v-if="loading" key="loading" class="editor-loading" aria-busy="true" aria-live="polite">
      <ProgressSpinner v-if="showLoading" aria-label="Loading extension files" />
    </div>

    <div v-else-if="currentFile" key="editor" class="code-editor-wrapper">
      <CodeEditor
        v-model="currentFile.content"
        :language="getFileLanguage(currentFile.name).toLowerCase()"
        theme="bitm-dark"
        @change="$emit('change')"
      />
    </div>

    <div v-else key="empty" class="no-file-selected">
      <i class="pi pi-file"></i>
      <h3>No files uploaded yet</h3>
      <p>Upload existing files or create a new one to get started</p>
      <div class="no-file-actions">
        <Button
          label="Upload Files"
          icon="pi pi-upload"
          @click="$emit('upload-click')"
        />
        <Button
          label="Create New File"
          icon="pi pi-plus"
          severity="secondary"
          outlined
          @click="$emit('new-file-click')"
        />
      </div>
    </div>
    </Transition>

    <div v-if="!loading && currentFile" class="status-bar">
      <div class="status-left">
        <span class="status-item">
          <i class="pi pi-code"></i>
          {{ getFileLanguage(currentFile.name) }}
        </span>
        <span class="status-item">
          <i class="pi pi-list"></i>
          {{ lineCount }} lines
        </span>
        <span class="status-item">
          <i class="pi pi-file"></i>
          {{ fileSize }}
        </span>
      </div>
      <div class="status-right">
        <Button
          icon="pi pi-copy"
          severity="secondary"
          text
          rounded
          size="small"
          @click="$emit('copy')"
          v-tooltip.top="'Copy to clipboard'"
        />
        <Button
          icon="pi pi-align-justify"
          severity="secondary"
          text
          rounded
          size="small"
          @click="$emit('format')"
          v-tooltip.top="'Format code'"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'
import CodeEditor from '@/components/default/CodeEditor.vue'

defineProps({
  openTabs: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  showLoading: { type: Boolean, default: false },
  currentFile: { type: Object, default: null },
  isFileModified: { type: Function, required: true },
  getFileIcon: { type: Function, required: true },
  getFileLanguage: { type: Function, required: true },
  lineCount: { type: Number, default: 0 },
  fileSize: { type: String, default: '0 B' }
})

defineEmits(['switch-tab', 'close-tab', 'change', 'upload-click', 'new-file-click', 'copy', 'format'])
</script>

<style scoped>
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--code-canvas);
}

.editor-tabs {
  display: flex;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);
  padding: 0 0.5rem;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--code-border) var(--code-surface);
}

.editor-tabs::-webkit-scrollbar {
  height: 4px;
}

.editor-tabs::-webkit-scrollbar-track {
  background: var(--code-surface);
}

.editor-tabs::-webkit-scrollbar-thumb {
  background: var(--code-border);
  border-radius: 2px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  background: var(--code-raised);
  border: 1px solid transparent;
  border-bottom: none;
  font-size: 0.875rem;
  color: var(--code-muted);
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
  transition: var(--transition-interactive);
  white-space: nowrap;
}

.tab:hover {
  background: var(--code-canvas);
  color: var(--code-text);
}

.tab.active {
  background: var(--code-canvas);
  color: var(--code-text);
  border-bottom: 2px solid var(--primary-color);
}

.tab i {
  font-size: 0.813rem;
}

.unsaved-indicator {
  color: var(--primary-color);
  font-size: 1.25rem;
  line-height: 0;
  margin-left: -0.25rem;
}

.close-tab-btn {
  width: 20px;
  height: 20px;
  padding: 0;
  margin-left: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s ease;
  color: var(--code-text);
}

.tab:hover .close-tab-btn,
.tab.active .close-tab-btn {
  opacity: 1;
}

.close-tab-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.code-editor-wrapper {
  flex: 1;
  overflow: hidden;
}

.editor-loading {
  display: grid;
  flex: 1;
  min-height: 0;
  place-items: center;
  background: var(--code-canvas);
}

.editor-loading :deep(.p-progressspinner) {
  width: 2.5rem;
  height: 2.5rem;
}

.no-file-selected {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--code-muted);
  background: var(--code-canvas);
  padding: 2rem;
}

.no-file-selected i {
  font-size: 4rem;
  opacity: 0.5;
}

.no-file-selected h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--code-text);
}

.no-file-selected p {
  margin: 0;
  font-size: 0.875rem;
  text-align: center;
}

.no-file-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: var(--code-raised);
  border-top: 1px solid var(--code-border);
  color: var(--code-text);
  font-size: 0.813rem;
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.status-item i {
  font-size: 0.75rem;
}

.status-bar :deep(.p-button) {
  color: var(--code-muted);
}

.status-bar :deep(.p-button:hover) {
  background: var(--code-surface);
  color: var(--code-text);
}

@media (max-width: 768px) {
  .status-bar {
    font-size: 0.75rem;
  }

  .status-left,
  .status-right {
    gap: 0.5rem;
  }

  .no-file-actions {
    flex-direction: column;
    width: 100%;
  }

  .tab {
    padding: 0.5rem 0.625rem;
    font-size: 0.813rem;
  }
}
</style>
