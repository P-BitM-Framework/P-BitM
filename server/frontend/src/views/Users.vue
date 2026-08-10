<template>
  <div class="users-view app-page">
    <DelayedContent :loading="loading" :show-indicator="showLoading">
    <PageHeader
      title="Team"
      subtitle="Manage administrators and red team operators"
    >
      <template #actions>
        <Button label="New User" icon="pi pi-user-plus" @click="openCreateDialog" />
      </template>
    </PageHeader>

    <div class="metrics-grid team-metrics">
      <Card class="metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-users"></i>
            <div>
              <div class="stat-value">{{ users.length }}</div>
              <div class="stat-label">Team Members</div>
            </div>
          </div>
        </template>
      </Card>
      <Card class="metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-shield"></i>
            <div>
              <div class="stat-value">{{ adminCount }}</div>
              <div class="stat-label">Administrators</div>
            </div>
          </div>
        </template>
      </Card>
      <Card class="metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-briefcase"></i>
            <div>
              <div class="stat-value">{{ operatorCount }}</div>
              <div class="stat-label">Operators</div>
            </div>
          </div>
        </template>
      </Card>
      <Card class="metric-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-user-minus"></i>
            <div>
              <div class="stat-value">{{ disabledCount }}</div>
              <div class="stat-label">Disabled</div>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <Card class="app-table-card">
      <template #content>
        <div class="app-table-header team-table-header">
          <h2 class="app-section-title">
            <i class="pi pi-id-card"></i>
            Team Access
            <span class="count-badge">{{ users.length }}</span>
          </h2>

          <div class="app-table-controls">
            <IconField iconPosition="left">
              <InputIcon><i class="pi pi-search" /></InputIcon>
              <InputText
                v-model="filters.global.value"
                placeholder="Search users..."
              />
            </IconField>
            <Button
              icon="pi pi-refresh"
              severity="secondary"
              text
              rounded
              :loading="showLoading"
              @click="fetchUsers"
              v-tooltip.bottom="'Refresh'"
            />
          </div>
        </div>

        <DataTable
          :value="users"
          :loading="showLoading"
          :filters="filters"
          paginator
          :rows="25"
          :rowsPerPageOptions="[10, 25, 50]"
          class="data-table data-table--interactive"
          @row-click="openEditDialog($event.data)"
        >
          <Column field="username" header="User" sortable style="min-width: 220px">
            <template #body="{ data }">
              <div class="user-cell">
                <i :class="data.role === 'admin' ? 'pi pi-shield' : 'pi pi-user'"></i>
                <div>
                  <strong>{{ data.username }}</strong>
                  <span v-if="data.id === authStore.user?.id" class="current-user">You</span>
                </div>
              </div>
            </template>
          </Column>

          <Column field="email" header="Email" sortable style="min-width: 260px" />

          <Column field="role" header="Role" sortable style="width: 150px">
            <template #body="{ data }">
              <Tag
                :value="roleLabel(data.role)"
                :severity="data.role === 'admin' ? 'warn' : 'info'"
              />
            </template>
          </Column>

          <Column field="is_active" header="Status" sortable style="width: 140px">
            <template #body="{ data }">
              <Tag
                :value="data.is_active ? 'Active' : 'Disabled'"
                :severity="data.is_active ? 'success' : 'secondary'"
                :icon="data.is_active ? 'pi pi-check-circle' : 'pi pi-ban'"
              />
            </template>
          </Column>

          <Column field="last_login" header="Last Login" sortable style="width: 200px">
            <template #body="{ data }">
              <span :class="{ 'text-muted': !data.last_login }">
                {{ formatDate(data.last_login) }}
              </span>
            </template>
          </Column>

          <Column header="Actions" style="width: 190px" headerClass="sticky-actions" bodyClass="sticky-actions" exportable="false">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-key"
                  severity="secondary"
                  text
                  rounded
                  @click.stop="openPasswordDialog(data)"
                  v-tooltip.top="'Reset password'"
                />
                <Button
                  :icon="data.is_active ? 'pi pi-user-minus' : 'pi pi-user-plus'"
                  :severity="data.is_active ? 'warn' : 'success'"
                  text
                  rounded
                  :disabled="data.id === authStore.user?.id"
                  @click.stop="toggleUser(data)"
                  v-tooltip.top="data.id === authStore.user?.id
                    ? 'You cannot disable your own account'
                    : (data.is_active ? 'Disable' : 'Enable')"
                />
                <Button
                  icon="pi pi-pencil"
                  severity="secondary"
                  text
                  rounded
                  @click.stop="openEditDialog(data)"
                  v-tooltip.top="'Edit'"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  :disabled="data.id === authStore.user?.id"
                  @click.stop="openDeleteDialog(data)"
                  v-tooltip.top="data.id === authStore.user?.id
                    ? 'You cannot delete your own account'
                    : 'Delete'"
                />
              </div>
            </template>
          </Column>

          <template #empty>
            <div class="empty-state">
              <i class="pi pi-users"></i>
              <p>No users found.</p>
              <Button
                label="Create User"
                icon="pi pi-user-plus"
                size="small"
                @click="openCreateDialog"
              />
            </div>
          </template>
        </DataTable>
      </template>
    </Card>
    </DelayedContent>

    <Dialog
      v-model:visible="showUserDialog"
      modal
      :header="dialogMode === 'create' ? 'Create User' : 'Edit User'"
      :style="{ width: '640px' }"
      :draggable="false"
      @hide="resetUserForm"
    >
      <div class="user-form">
        <div class="field-row">
          <div class="field">
            <label for="username">Username <span class="required">*</span></label>
            <InputText
              id="username"
              v-model.trim="userForm.username"
              class="w-full"
              placeholder="redteam.operator"
              :disabled="dialogMode === 'edit'"
              :invalid="submitted && !validUsername"
            />
            <small v-if="submitted && !validUsername" class="p-error">
              Use 3-64 letters, numbers, dots, dashes, or underscores.
            </small>
          </div>
          <div class="field">
            <label for="role">Role <span class="required">*</span></label>
            <Select
              id="role"
              v-model="userForm.role"
              :options="roleOptions"
              optionLabel="label"
              optionValue="value"
              class="w-full"
            />
          </div>
        </div>

        <div class="field">
          <label for="email">Email <span class="required">*</span></label>
          <InputText
            id="email"
            v-model.trim="userForm.email"
            type="email"
            class="w-full"
            placeholder="operator@example.com"
            :invalid="submitted && !validEmail"
          />
          <small v-if="submitted && !validEmail" class="p-error">
            Enter a valid email address.
          </small>
        </div>

        <Message v-if="dialogMode === 'create'" severity="info" :closable="false">
          A secure temporary password will be generated automatically after the user is created.
        </Message>

        <div v-else class="access-toggle">
          <div>
            <strong>Account access</strong>
            <span>{{ userForm.is_active ? 'The user can sign in.' : 'Sign-in is blocked.' }}</span>
          </div>
          <ToggleSwitch
            v-model="userForm.is_active"
            :disabled="selectedUser?.id === authStore.user?.id"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showUserDialog = false" />
        <Button
          :label="dialogMode === 'create' ? 'Create User' : 'Save Changes'"
          :icon="dialogMode === 'create' ? 'pi pi-user-plus' : 'pi pi-check'"
          :loading="saving"
          @click="saveUser"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showPasswordDialog"
      modal
      header="Reset Password"
      :style="{ width: '500px' }"
      :draggable="false"
      @hide="resetPasswordForm"
    >
      <div class="user-form">
        <Message severity="info" :closable="false">
          Generate a new temporary password for <strong>{{ selectedUser?.username }}</strong>.
          Existing sessions will be revoked immediately.
        </Message>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showPasswordDialog = false" />
        <Button
          label="Reset Password"
          icon="pi pi-key"
          :loading="resettingPassword"
          @click="resetPassword"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showCredentialDialog"
      modal
      header="Temporary Password"
      :style="{ width: '520px' }"
      :draggable="false"
      :close-on-escape="false"
      @hide="clearGeneratedCredential"
    >
      <div class="user-form">
        <Message severity="warn" :closable="false">
          Copy this password now and share it securely with
          <strong>{{ generatedCredential.username }}</strong>. It will not be shown again.
        </Message>
        <div class="field">
          <label for="generatedPassword">Generated password</label>
          <div class="credential-field">
            <InputText
              id="generatedPassword"
              :model-value="generatedCredential.password"
              class="w-full credential-value"
              readonly
            />
            <Button
              :icon="credentialCopied ? 'pi pi-check' : 'pi pi-copy'"
              :label="credentialCopied ? 'Copied' : 'Copy'"
              severity="secondary"
              @click="copyGeneratedPassword"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <Button label="Done" icon="pi pi-check" @click="showCredentialDialog = false" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showDeleteDialog"
      modal
      header="Delete User"
      :style="{ width: '500px' }"
      :draggable="false"
    >
      <div class="dialog-content">
        <div class="dialog-icon"><i class="pi pi-exclamation-triangle"></i></div>
        <h3>Delete “{{ selectedUser?.username }}”?</h3>
        <p>The account will be permanently removed.</p>
        <Message severity="warn" :closable="false">
          Campaigns owned by this user will be transferred to your admin account.
        </Message>
      </div>

      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="showDeleteDialog = false" />
        <Button
          label="Delete User"
          icon="pi pi-trash"
          severity="danger"
          :loading="deleting"
          @click="deleteUser"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { FilterMatchMode } from '@primevue/core/api'
import { useToast } from 'primevue/usetoast'
import PageHeader from '@/components/default/PageHeader.vue'
import DelayedContent from '@/components/default/DelayedContent.vue'
import { backendService } from '@/services/backend'
import { useAuthStore } from '@/stores/auth'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Select from 'primevue/select'
import { useDelayedIndicator } from '@/composables/useDelayedIndicator'

const toast = useToast()
const authStore = useAuthStore()

const users = ref([])
const loading = ref(true)
const showLoading = useDelayedIndicator(loading)
const saving = ref(false)
const deleting = ref(false)
const resettingPassword = ref(false)
const submitted = ref(false)
const dialogMode = ref('create')
const selectedUser = ref(null)
const showUserDialog = ref(false)
const showPasswordDialog = ref(false)
const showDeleteDialog = ref(false)
const showCredentialDialog = ref(false)
const credentialCopied = ref(false)
const generatedCredential = ref({ username: '', password: '' })

const roleOptions = [
  { label: 'Administrator', value: 'admin' },
  { label: 'Red Team Operator', value: 'operator' }
]

const emptyUserForm = () => ({
  username: '',
  email: '',
  role: 'operator',
  is_active: true
})

const userForm = ref(emptyUserForm())
const filters = ref({
  global: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const adminCount = computed(() => users.value.filter((user) => user.role === 'admin').length)
const operatorCount = computed(() => users.value.filter((user) => user.role === 'operator').length)
const disabledCount = computed(() => users.value.filter((user) => !user.is_active).length)
const validUsername = computed(() => /^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$/.test(userForm.value.username))
const validEmail = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(userForm.value.email))

function roleLabel(role) {
  return role === 'admin' ? 'Administrator' : 'Operator'
}

function formatDate(value) {
  if (!value) return 'Never'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Never'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date)
}

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await backendService.getUsers()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to load team',
      detail: error.message,
      life: 3500
    })
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  dialogMode.value = 'create'
  selectedUser.value = null
  userForm.value = emptyUserForm()
  submitted.value = false
  showUserDialog.value = true
}

function openEditDialog(user) {
  dialogMode.value = 'edit'
  selectedUser.value = user
  userForm.value = {
    ...emptyUserForm(),
    username: user.username,
    email: user.email,
    role: user.role,
    is_active: user.is_active
  }
  submitted.value = false
  showUserDialog.value = true
}

function resetUserForm() {
  submitted.value = false
  userForm.value = emptyUserForm()
}

async function saveUser() {
  submitted.value = true
  if (!validUsername.value || !validEmail.value) return

  saving.value = true
  try {
    if (dialogMode.value === 'create') {
      const createdUser = await backendService.createUser({
        username: userForm.value.username,
        email: userForm.value.email,
        role: userForm.value.role
      })
      generatedCredential.value = {
        username: createdUser.username,
        password: createdUser.temporary_password
      }
      toast.add({
        severity: 'success',
        summary: 'User created',
        detail: 'A temporary password was generated securely.',
        life: 3000
      })
      showCredentialDialog.value = true
    } else {
      await backendService.updateUser(selectedUser.value.id, {
        email: userForm.value.email,
        role: userForm.value.role,
        is_active: userForm.value.is_active
      })
      toast.add({
        severity: 'success',
        summary: 'User updated',
        detail: `Changes to ${userForm.value.username} were saved.`,
        life: 3000
      })
    }
    showUserDialog.value = false
    await fetchUsers()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to save user',
      detail: error.message,
      life: 4000
    })
  } finally {
    saving.value = false
  }
}

async function toggleUser(user) {
  try {
    await backendService.updateUser(user.id, { is_active: !user.is_active })
    toast.add({
      severity: 'success',
      summary: user.is_active ? 'User disabled' : 'User enabled',
      detail: user.username,
      life: 2500
    })
    await fetchUsers()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to update access',
      detail: error.message,
      life: 4000
    })
  }
}

function openPasswordDialog(user) {
  selectedUser.value = user
  showPasswordDialog.value = true
}

function resetPasswordForm() {
  resettingPassword.value = false
}

async function resetPassword() {
  resettingPassword.value = true
  try {
    const result = await backendService.resetUserPassword(selectedUser.value.id)
    generatedCredential.value = {
      username: selectedUser.value.username,
      password: result.temporary_password
    }
    showPasswordDialog.value = false
    showCredentialDialog.value = true
    toast.add({
      severity: 'success',
      summary: 'Password reset',
      detail: `A temporary password was generated for ${selectedUser.value.username}.`,
      life: 3000
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to reset password',
      detail: error.message,
      life: 4000
    })
  } finally {
    resettingPassword.value = false
  }
}

function clearGeneratedCredential() {
  generatedCredential.value = { username: '', password: '' }
  credentialCopied.value = false
}

async function copyGeneratedPassword() {
  try {
    await navigator.clipboard.writeText(generatedCredential.value.password)
    credentialCopied.value = true
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Unable to copy password',
      detail: 'Select the password and copy it manually.',
      life: 3500
    })
  }
}

function openDeleteDialog(user) {
  selectedUser.value = user
  showDeleteDialog.value = true
}

async function deleteUser() {
  deleting.value = true
  try {
    const result = await backendService.deleteUser(selectedUser.value.id)
    showDeleteDialog.value = false
    toast.add({
      severity: 'success',
      summary: 'User deleted',
      detail: result.reassigned_campaigns
        ? `${result.reassigned_campaigns} campaign(s) were transferred to you.`
        : 'The account was permanently removed.',
      life: 3500
    })
    await fetchUsers()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Unable to delete user',
      detail: error.message,
      life: 4000
    })
  } finally {
    deleting.value = false
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.team-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 1.25rem;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-value {
  color: var(--color-heading);
  font-weight: 700;
}

.stat-label {
  margin-top: 0.15rem;
  color: var(--color-text-mute);
  font-size: 0.85rem;
}

.team-table-header,
.app-table-controls,
.app-section-title,
.user-cell,
.user-cell > div,
.access-toggle {
  display: flex;
  align-items: center;
}

.team-table-header,
.access-toggle {
  justify-content: space-between;
}

.app-section-title {
  gap: 0.65rem;
  margin: 0;
  color: var(--color-heading);
  font-size: 1.05rem;
  font-weight: 650;
}

.app-section-title > i,
.user-cell > i {
  color: var(--color-accent);
}

.app-table-controls {
  gap: 0.5rem;
}

.user-cell {
  gap: 0.75rem;
}

.user-cell > i {
  width: 20px;
  font-size: 1.05rem;
  text-align: center;
}

.user-cell > div {
  gap: 0.5rem;
}

.current-user {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
  color: var(--color-text-mute);
  font-size: 0.7rem;
  font-weight: 600;
}

.text-muted {
  color: var(--color-text-mute);
}

.user-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.access-toggle {
  min-height: 72px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 1rem;
}

.access-toggle > div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.access-toggle span {
  color: var(--color-text-mute);
  font-size: 0.85rem;
}

.w-full {
  width: 100%;
}

.credential-field {
  display: flex;
  gap: 0.75rem;
}

.credential-value {
  font-family: var(--font-mono);
  letter-spacing: 0.025em;
}
</style>
