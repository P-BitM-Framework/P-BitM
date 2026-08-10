import { describe, expect, it, vi } from 'vitest'

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    checked: true,
    isAuthenticated: true,
    isAdmin: true,
    checkAuth: vi.fn()
  })
}))

import router, { preloadRouteComponent } from '@/router'

describe('detail routes', () => {
  it('resolves a Target List identifier to its authenticated detail route', () => {
    const resolved = router.resolve({
      name: 'target-list',
      params: { listId: 'list-123' }
    })

    expect(resolved.href).toBe('/target-lists/list-123')
    expect(resolved.name).toBe('target-list')
    expect(resolved.params).toEqual({ listId: 'list-123' })
    expect(resolved.meta.requiresAuth).toBe(true)
  })

  it('resolves a Plugin identifier to its authenticated editor route', () => {
    const resolved = router.resolve({
      name: 'plugin-editor',
      params: { id: 'plugin-456' }
    })

    expect(resolved.href).toBe('/plugins/plugin-456/edit')
    expect(resolved.name).toBe('plugin-editor')
    expect(resolved.params).toEqual({ id: 'plugin-456' })
    expect(resolved.meta.requiresAuth).toBe(true)
  })

  it.each([
    ['target-list', 'TargetListDetail'],
    ['plugin-editor', 'PluginDetail']
  ])('loads the %s route component', async (routeName, componentName) => {
    const routeModule = await preloadRouteComponent(routeName)

    expect(routeModule.default.__name).toBe(componentName)
  })
})
