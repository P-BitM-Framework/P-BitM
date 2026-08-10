import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DelayedContent from '@/components/default/DelayedContent.vue'


function mountGate(props = {}) {
  return mount(DelayedContent, {
    props: {
      loading: true,
      showIndicator: false,
      ...props
    },
    slots: {
      default: '<section data-testid="page-content">Loaded page</section>'
    },
    global: {
      stubs: {
        ProgressSpinner: { template: '<span data-testid="spinner" />' }
      }
    }
  })
}

describe('DelayedContent', () => {
  it('keeps content mounted but hidden while loading without showing an early spinner', () => {
    const wrapper = mountGate()

    expect(wrapper.get('[data-testid="page-content"]').exists()).toBe(true)
    expect(wrapper.classes()).toContain('is-loading')
    expect(wrapper.find('[data-testid="spinner"]').exists()).toBe(false)
  })

  it('reveals the same mounted content when loading completes', async () => {
    const wrapper = mountGate({ showIndicator: true })

    expect(wrapper.find('[data-testid="spinner"]').exists()).toBe(true)
    await wrapper.setProps({ loading: false })

    expect(wrapper.classes()).not.toContain('is-loading')
    expect(wrapper.find('[data-testid="spinner"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="page-content"]').text()).toBe('Loaded page')
  })
})
