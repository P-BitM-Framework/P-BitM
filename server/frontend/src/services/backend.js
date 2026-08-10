import { createApiClient } from './api/http'
import { createAuthClient } from './api/auth'
import { createUsersClient } from './api/users'
import { createCampaignsClient } from './api/campaigns'
import { createVictimsClient } from './api/victims'
import { createLibraryClient } from './api/library'

const apiClient = createApiClient()

/**
 * Facade combining every resource-specific API client into the single
 * object components import. Keeps the call sites (`backendService.foo(...)`)
 * stable while the underlying clients stay independently maintainable.
 */
export const backendService = {
  ...createAuthClient(apiClient),
  ...createUsersClient(apiClient),
  ...createCampaignsClient(apiClient),
  ...createVictimsClient(apiClient),
  ...createLibraryClient(apiClient)
}
