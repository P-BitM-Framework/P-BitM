import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  router: {
    push: vi.fn()
  },
  toast: {
    add: vi.fn()
  },
  backendService: {
    getTargetLists: vi.fn(),
    createTargetList: vi.fn(),
    deleteTargetList: vi.fn(),
    getPlugins: vi.fn(),
    createPlugin: vi.fn(),
    exportPlugin: vi.fn(),
    deletePlugin: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => mocks.router
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => mocks.toast
}))

vi.mock('@/services/backend', () => ({
  backendService: mocks.backendService
}))

vi.mock('@iconify/vue', () => ({
  Icon: { template: '<span />' }
}))

import TargetLists from '@/views/TargetLists.vue'
import Plugins from '@/views/Plugins.vue'

const DataTableStub = defineComponent({
  name: 'DataTable',
  emits: ['row-click'],
  template: '<div><slot /></div>'
})

const CardStub = defineComponent({
  name: 'Card',
  template: '<section><slot name="content" /></section>'
})

function mountView(component) {
  return mount(component, {
    global: {
      directives: {
        tooltip: () => {}
      },
      stubs: {
        DataTable: DataTableStub,
        PageHeader: true,
        Card: CardStub,
        Column: true,
        Dialog: true,
        Button: true,
        IconField: true,
        InputIcon: true,
        InputText: true,
        Textarea: true,
        Message: true,
        ProgressSpinner: true,
        Tag: true
      }
    }
  })
}

describe('detail page navigation', () => {
  beforeEach(() => {
    mocks.backendService.getTargetLists.mockResolvedValue({
      target_lists: [{ id: 'list-123', name: 'Targets' }]
    })
    mocks.backendService.getPlugins.mockResolvedValue({
      plugins: [{ id: 'plugin-456', name: 'Example plugin', files: [] }]
    })
  })

  it('opens a Target List from its table row', async () => {
    const wrapper = mountView(TargetLists)
    await flushPromises()

    wrapper.findComponent({ name: 'DataTable' }).vm.$emit('row-click', {
      data: { id: 'list-123' }
    })

    expect(mocks.router.push).toHaveBeenCalledWith({
      name: 'target-list',
      params: { listId: 'list-123' }
    })
  })

  it('opens a newly created Target List using the returned identifier', async () => {
    mocks.backendService.createTargetList.mockResolvedValue({
      id: 'list-created',
      name: 'Created list'
    })
    const wrapper = mountView(TargetLists)
    await flushPromises()
    wrapper.vm.newList.name = 'Created list'

    await wrapper.vm.saveList()

    expect(mocks.backendService.createTargetList).toHaveBeenCalledWith({
      name: 'Created list',
      description: '',
      company: ''
    })
    expect(mocks.router.push).toHaveBeenCalledWith({
      name: 'target-list',
      params: { listId: 'list-created' }
    })
  })

  it('opens the Plugin Editor from its table row', async () => {
    const wrapper = mountView(Plugins)
    await flushPromises()

    wrapper.findComponent({ name: 'DataTable' }).vm.$emit('row-click', {
      data: { id: 'plugin-456' }
    })

    expect(mocks.router.push).toHaveBeenCalledWith({
      name: 'plugin-editor',
      params: { id: 'plugin-456' }
    })
  })

  it('opens the editor for a newly created Plugin', async () => {
    mocks.backendService.createPlugin.mockResolvedValue({
      id: 'plugin-created'
    })
    const wrapper = mountView(Plugins)
    await flushPromises()
    wrapper.vm.newPlugin.name = 'Created plugin'

    await wrapper.vm.createPlugin()

    expect(mocks.backendService.createPlugin).toHaveBeenCalledWith({
      name: 'Created plugin',
      description: ''
    })
    expect(mocks.router.push).toHaveBeenCalledWith({
      name: 'plugin-editor',
      params: { id: 'plugin-created' }
    })
  })
})
