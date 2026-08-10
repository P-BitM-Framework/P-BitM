import { nextTick } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  toast: { add: vi.fn() },
  router: { push: vi.fn() },
  backendService: {
    getPlugin: vi.fn(),
    updatePlugin: vi.fn(),
    exportPlugin: vi.fn(),
    deletePlugin: vi.fn()
  }
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => mocks.toast
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'plugin-1' } }),
  useRouter: () => mocks.router
}))

vi.mock('@/services/backend', () => ({
  backendService: mocks.backendService
}))

vi.mock('@iconify/vue', () => ({
  Icon: { template: '<span />' }
}))

import PluginDetail from '@/views/PluginDetail.vue'
import PluginEditorToolbar from '@/components/plugin/PluginEditorToolbar.vue'
import PluginSettingsPanel from '@/components/plugin/PluginSettingsPanel.vue'

function mountEditor() {
  return shallowMount(PluginDetail, {
    global: {
      directives: {
        tooltip: () => {}
      },
      stubs: {
        DelayedContent: { template: '<div><slot /></div>' },
        Dialog: true,
        Divider: true,
        Button: true,
        Message: true,
        InputText: true
      }
    }
  })
}

describe('PluginDetail', () => {
  beforeEach(() => {
    mocks.backendService.getPlugin.mockResolvedValue({
      id: 'plugin-1',
      name: 'Example plugin',
      description: 'Original description',
      files: [{ name: 'main.js', content: 'console.log("original")' }]
    })
    mocks.backendService.updatePlugin.mockResolvedValue({})
  })

  it('enables Save from the canonical files state and persists edited files', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    expect(
      wrapper.findComponent(PluginEditorToolbar).props('saveDisabled')
    ).toBe(false)

    wrapper.vm.files[0].content = 'console.log("edited")'
    wrapper.vm.markCurrentUnsaved()
    await wrapper.vm.savePlugin()

    expect(mocks.backendService.updatePlugin).toHaveBeenCalledWith(
      'plugin-1',
      {
        name: 'Example plugin',
        description: 'Original description',
        files: [{ name: 'main.js', content: 'console.log("edited")' }]
      }
    )
    expect(wrapper.vm.hasUnsavedChanges).toBe(false)
  })

  it('marks settings edits as unsaved even without a current file', async () => {
    mocks.backendService.getPlugin.mockResolvedValue({
      id: 'plugin-1',
      name: 'Empty plugin',
      description: '',
      files: []
    })
    const wrapper = mountEditor()
    await flushPromises()

    wrapper.findComponent(PluginSettingsPanel).vm.$emit('edited')
    await nextTick()

    expect(wrapper.vm.currentFile).toBeNull()
    expect(wrapper.vm.hasUnsavedChanges).toBe(true)
  })

  it('allows an initially empty plugin to become savable after creating a file', async () => {
    mocks.backendService.getPlugin.mockResolvedValue({
      id: 'plugin-1',
      name: 'Empty plugin',
      description: '',
      files: []
    })
    const wrapper = mountEditor()
    await flushPromises()

    expect(
      wrapper.findComponent(PluginEditorToolbar).props('saveDisabled')
    ).toBe(true)

    wrapper.vm.newFileName = 'nested/main.js'
    wrapper.vm.createFile()
    await nextTick()

    expect(wrapper.vm.files).toEqual([
      expect.objectContaining({ name: 'nested/main.js' })
    ])
    expect(wrapper.vm.currentFile.name).toBe('nested/main.js')
    expect(wrapper.vm.isFileModified('nested/main.js')).toBe(true)
    expect(
      wrapper.findComponent(PluginEditorToolbar).props('saveDisabled')
    ).toBe(false)
  })

  it('clears the deleted file state while keeping the plugin dirty', async () => {
    const wrapper = mountEditor()
    await flushPromises()

    wrapper.vm.markCurrentUnsaved()
    wrapper.vm.confirmDeleteFile(wrapper.vm.files[0])
    wrapper.vm.deleteFile()

    expect(wrapper.vm.files).toEqual([])
    expect(wrapper.vm.currentFile).toBeNull()
    expect(wrapper.vm.isFileModified('main.js')).toBe(false)
    expect(wrapper.vm.hasUnsavedChanges).toBe(true)
  })
})
