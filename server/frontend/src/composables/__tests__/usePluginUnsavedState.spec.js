import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { usePluginUnsavedState } from '@/composables/usePluginUnsavedState'

const Harness = defineComponent({
  setup() {
    return usePluginUnsavedState()
  },
  template: '<div />'
})

describe('usePluginUnsavedState', () => {
  it('tracks file and plugin metadata changes independently', () => {
    const wrapper = mount(Harness)

    wrapper.vm.markUnsaved('main.js')
    wrapper.vm.markPluginUnsaved()

    expect(wrapper.vm.isFileModified('main.js')).toBe(true)
    expect(wrapper.vm.hasUnsavedChanges).toBe(true)

    wrapper.vm.clearUnsaved('main.js')

    expect(wrapper.vm.isFileModified('main.js')).toBe(false)
    expect(wrapper.vm.hasUnsavedChanges).toBe(true)

    wrapper.vm.clearUnsaved()
    expect(wrapper.vm.hasUnsavedChanges).toBe(false)
  })

  it('warns before unload only while changes are pending', () => {
    const wrapper = mount(Harness)
    const cleanEvent = new Event('beforeunload', { cancelable: true })

    window.dispatchEvent(cleanEvent)
    expect(cleanEvent.defaultPrevented).toBe(false)

    wrapper.vm.markUnsaved('main.js')
    const dirtyEvent = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(dirtyEvent)

    expect(dirtyEvent.defaultPrevented).toBe(true)
    wrapper.unmount()
  })

  it('removes the beforeunload listener when the owner unmounts', () => {
    const removeEventListener = vi.spyOn(window, 'removeEventListener')
    const wrapper = mount(Harness)

    wrapper.unmount()

    expect(removeEventListener).toHaveBeenCalledWith(
      'beforeunload',
      expect.any(Function)
    )
  })
})
