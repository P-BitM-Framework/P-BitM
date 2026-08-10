<template>
  <div class="monaco-editor-wrapper">
    <VueMonacoEditor
      v-model:value="localValue"
      :language="language"
      :theme="theme"
      :options="editorOptions"
      @beforeMount="handleBeforeMount"
      @mount="handleMount"
      @change="handleChange"
      class="code-editor"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'javascript'
  },
  theme: {
    type: String,
    default: 'bitm-dark'
  },
  readOnly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localValue = ref(props.modelValue)
let editorInstance = null

const handleBeforeMount = (monaco) => {
  monaco.editor.defineTheme('bitm-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: '', foreground: 'ABB2BF', background: '141419' },
      { token: 'comment', foreground: '5C6370', fontStyle: 'italic' },
      { token: 'comment.doc', foreground: '5C6370', fontStyle: 'italic' },
      { token: 'comment.doc.tag', foreground: 'C678DD' },
      { token: 'keyword', foreground: 'C678DD' },
      { token: 'keyword.control', foreground: 'C678DD' },
      { token: 'operator', foreground: '56B6C2' },
      { token: 'delimiter', foreground: 'ABB2BF' },
      { token: 'delimiter.bracket', foreground: 'ABB2BF' },
      { token: 'string', foreground: '98C379' },
      { token: 'string.escape', foreground: '56B6C2' },
      { token: 'string.invalid', foreground: 'E06C75' },
      { token: 'regexp', foreground: 'E06C75' },
      { token: 'number', foreground: 'D19A66' },
      { token: 'number.hex', foreground: 'D19A66' },
      { token: 'constant', foreground: 'D19A66' },
      { token: 'constant.language', foreground: 'D19A66' },
      { token: 'identifier', foreground: 'ABB2BF' },
      { token: 'variable', foreground: 'E06C75' },
      { token: 'variable.predefined', foreground: 'E5C07B' },
      { token: 'variable.parameter', foreground: 'D19A66' },
      { token: 'type', foreground: 'E5C07B' },
      { token: 'type.identifier', foreground: 'E5C07B' },
      { token: 'class', foreground: 'E5C07B' },
      { token: 'namespace', foreground: 'E5C07B' },
      { token: 'function', foreground: '61AFEF' },
      { token: 'function.call', foreground: '61AFEF' },
      { token: 'property', foreground: '56B6C2' },
      { token: 'annotation', foreground: 'D19A66' },
      { token: 'tag', foreground: 'E06C75' },
      { token: 'attribute.name', foreground: 'D19A66' },
      { token: 'attribute.value', foreground: '98C379' },
      { token: 'metatag', foreground: '56B6C2' },
      { token: 'tag.html', foreground: 'E06C75' },
      { token: 'delimiter.html', foreground: 'ABB2BF' },
      { token: 'attribute.name.html', foreground: 'D19A66' },
      { token: 'attribute.value.html', foreground: '98C379' },
      { token: 'metatag.html', foreground: '56B6C2' },
      { token: 'tag.css', foreground: '61AFEF' },
      { token: 'attribute.name.css', foreground: '56B6C2' },
      { token: 'attribute.value.css', foreground: 'ABB2BF' },
      { token: 'keyword.css', foreground: 'C678DD' },
      { token: 'number.css', foreground: 'D19A66' },
      { token: 'string.css', foreground: '98C379' },
      { token: 'string.key.json', foreground: 'E06C75' },
      { token: 'string.value.json', foreground: '98C379' },
      { token: 'number.json', foreground: 'D19A66' },
      { token: 'keyword.json', foreground: 'C678DD' },
      { token: 'keyword.md', foreground: 'C678DD' },
      { token: 'string.link.md', foreground: '61AFEF', fontStyle: 'underline' },
      { token: 'variable.md', foreground: 'E06C75' },
      { token: 'type.md', foreground: 'E5C07B', fontStyle: 'bold' }
    ],
    colors: {
      'editor.background': '#141419',
      'editor.foreground': '#ABB2BF',
      'editorLineNumber.foreground': '#6F6F7A',
      'editorLineNumber.activeForeground': '#C4C4CC',
      'editorCursor.foreground': '#F4F4F5',
      'editor.lineHighlightBackground': '#1B1B21',
      'editor.selectionBackground': '#2B303A',
      'editor.inactiveSelectionBackground': '#242831',
      'editor.selectionHighlightBackground': '#3A3F4966',
      'editorIndentGuide.background1': '#2B2B33',
      'editorIndentGuide.activeBackground1': '#555560',
      'editorWhitespace.foreground': '#35353F',
      'editorGutter.background': '#141419',
      'editorWidget.background': '#1B1B21',
      'editorWidget.border': '#35353F',
      'editorSuggestWidget.background': '#1B1B21',
      'editorSuggestWidget.border': '#35353F',
      'editorSuggestWidget.selectedBackground': '#303038',
      'minimap.background': '#141419',
      'scrollbarSlider.background': '#49495266',
      'scrollbarSlider.hoverBackground': '#6F6F7A88',
      'scrollbarSlider.activeBackground': '#92929DAA'
    }
  })
}

const editorOptions = {
  automaticLayout: true,
  fontSize: 14,
  lineNumbers: 'on',
  roundedSelection: true,
  scrollBeyondLastLine: false,
  renderWhitespace: 'selection',
  tabSize: 2,
  wordWrap: 'on',
  minimap: {
    enabled: true
  },
  readOnly: props.readOnly,
  formatOnPaste: true,
  formatOnType: true,
  suggestOnTriggerCharacters: true,
  quickSuggestions: {
    other: true,
    comments: true,
    strings: true
  },
  acceptSuggestionOnEnter: 'on',
  padding: {
    top: 16,
    bottom: 16
  }
}

const handleMount = (editor) => {
  editorInstance = editor
}

const handleChange = (value) => {
  emit('update:modelValue', value)
  emit('change', value)
}

// Sync external changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== localValue.value) {
    localValue.value = newValue
  }
})

// Watch language changes
watch(() => props.language, () => {
  // Language change is handled automatically by the component
})

// Expose methods for parent component
defineExpose({
  getEditor: () => editorInstance,
  getValue: () => localValue.value,
  setValue: (value) => { localValue.value = value },
  focus: () => editorInstance?.focus(),
  format: () => {
    if (editorInstance) {
      editorInstance.getAction('editor.action.formatDocument')?.run()
    }
  }
})
</script>

<style scoped>
.monaco-editor-wrapper {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: var(--code-canvas);
}

.code-editor {
  width: 100%;
  height: 100%;
}

:deep(.monaco-editor) {
  padding: 0;
}

:deep(.monaco-editor .margin) {
  background-color: var(--code-canvas);
}
</style>
