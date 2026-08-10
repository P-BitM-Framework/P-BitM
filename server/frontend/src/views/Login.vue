<template>
  <div class="login-container">
    <div class="login-theme">
      <SwitchTheme />
    </div>
    <div class="login-wrapper">
      <div class="login-header">
        <img src="@/assets/images/logo.webp" alt="BITM Logo" class="login-logo" />
        <p class="login-eyebrow">P-BitM Admin Dashboard</p>
        <h1 class="login-brand">Sign in</h1>
        <p class="login-subtitle">Sign in to manage campaigns and live sessions.</p>
      </div>

      <!-- Login Card -->
      <Card class="login-card">
        <template #content>
          <form @submit.prevent="onLogin" class="login-form">
            <!-- Username Field -->
            <div class="field">
              <label for="username" class="field-label">Username</label>
              <InputText
                id="username"
                v-model="username"
                placeholder="Enter your username"
                autocomplete="username"
                :class="{ 'p-invalid': error }"
                autofocus
              />
            </div>

            <!-- Password Field -->
            <div class="field">
              <label for="password" class="field-label">Password</label>
              <Password
                id="password"
                v-model="password"
                placeholder="Enter your password"
                toggleMask
                :feedback="false"
                autocomplete="current-password"
                :class="{ 'p-invalid': error }"
              >
                <template #footer>
                  <Divider />
                  <p class="mt-2">Minimum 8 characters</p>
                </template>
              </Password>
            </div>

            <!-- Error Message -->
            <Message v-if="error" severity="error" :closable="false" class="error-message">
              {{ error }}
            </Message>

            <!-- Login Button -->
            <Button
              label="Sign In"
              type="submit"
              :loading="loading"
              icon="pi pi-sign-in"
              class="login-button"
            />
          </form>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Password from 'primevue/password'
import SwitchTheme from '@/components/sidebar/SwitchTheme.vue'
import { backendService } from '@/services/backend'
import { useAuthStore } from '@/stores/auth'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const onLogin = async () => {
  // Validation
  if (!username.value || !password.value) {
    error.value = 'Username and password are required'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await backendService.login(username.value, password.value)
    const user = response.user

    auth.setSession(user, response.csrf_token)

    // Success toast
    toast.add({
      severity: 'success',
      summary: 'Signed in',
      detail: `Logged in as ${user.username}`,
      life: 3000
    })

    // Redirect to dashboard
    router.push('/')
  } catch (e) {
    console.error('Login error:', e)
    error.value = e.message || 'Invalid username or password'

    // Error toast
    toast.add({
      severity: 'error',
      summary: 'Login Failed',
      detail: error.value,
      life: 5000
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1.5rem, 4vw, 3.5rem);
  overflow: hidden;
  background:
    radial-gradient(circle at 18% 15%, var(--primary-subtle-strong), transparent 28rem),
    radial-gradient(circle at 85% 88%, var(--primary-subtle), transparent 32rem),
    var(--surface-canvas);
}

.login-theme {
  position: absolute;
  top: 1.25rem;
  right: 1.25rem;
  z-index: 2;
  width: 180px;
}

.login-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
  animation: fadeInUp 320ms var(--ease-standard);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header */
.login-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.login-logo {
  width: 132px;
  height: 132px;
  margin-bottom: 0.75rem;
  object-fit: contain;
}

.login-eyebrow {
  margin: 0 0 0.45rem;
  color: var(--primary);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.login-brand {
  margin: 0 0 0.4rem;
  color: var(--text-primary);
  font-size: 2rem;
  font-weight: 720;
  letter-spacing: -0.04em;
}

.login-subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.92rem;
}

/* Card */
.login-card {
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--surface-card) 94%, transparent);
  box-shadow: none;
  backdrop-filter: blur(18px);
  overflow: hidden;
}

.login-card :deep(.p-card-body) {
  padding: 0;
}

.login-card :deep(.p-card-content) {
  padding: 1.75rem;
}

/* Form */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.125rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-size: 0.84rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

/* Input styles */
.login-form :deep(.p-inputtext),
.login-form :deep(.p-password-input) {
  width: 100%;
  min-height: 44px;
  font-size: 0.95rem;
}

.login-form :deep(.p-password) {
  width: 100%;
}

.login-form :deep(.p-password-panel) {
  padding: 1rem;
}

/* Error message */
.error-message {
  margin: 0;
}

.error-message :deep(.p-inline-message) {
  width: 100%;
}

/* Login button */
.login-button {
  width: 100%;
  min-height: 44px;
  margin-top: 0.25rem;
  font-size: 0.94rem;
  font-weight: 600;
  border-radius: var(--radius-sm);
  background: var(--primary);
  border: none;
  color: var(--primary-on);
  transition:
    background-color var(--duration-normal) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}

.login-button:hover:not(:disabled) {
  background: var(--primary-hover);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

/* Divider */
.login-form :deep(.p-divider) {
  margin: 0.5rem 0;
}

@media (max-height: 760px) {
  .login-logo {
    width: 96px;
    height: 96px;
  }

  .login-header {
    margin-bottom: 1rem;
  }
}
</style>
