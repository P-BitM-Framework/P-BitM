import { describe, expect, it, vi } from 'vitest'

import { createUsersClient } from '@/services/api/users'


describe('users password payloads', () => {
  it('requests a server-generated password when creating a user', async () => {
    const request = vi.fn().mockResolvedValue({ temporary_password: 'generated' })
    const client = createUsersClient({ request })

    await client.createUser({
      username: 'operator',
      email: 'operator@example.com',
      role: 'operator'
    })

    expect(JSON.parse(request.mock.calls[0][1].body)).toEqual({
      username: 'operator',
      email: 'operator@example.com',
      role: 'operator'
    })
  })

  it('does not send a user-selected password during an admin reset', async () => {
    const request = vi.fn().mockResolvedValue({ temporary_password: 'generated' })
    const client = createUsersClient({ request })

    await client.resetUserPassword('user-1')

    expect(request).toHaveBeenCalledWith('api/users/user-1/reset-password', {
      method: 'POST',
      body: '{}'
    })
  })

  it('sends only the current password when changing the signed-in password', async () => {
    const request = vi.fn().mockResolvedValue({ temporary_password: 'generated' })
    const client = createUsersClient({ request })

    await client.changePassword('current-password')

    expect(JSON.parse(request.mock.calls[0][1].body)).toEqual({
      old_password: 'current-password'
    })
  })
})
