<template>
  <div class="waves-password-dialog">
    <div class="waves-dialog-container">
      <div class="waves-dialog-header">
        <div class="waves-header-content">
          <div class="waves-header-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M20 21H4a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2ZM7 9V7a5 5 0 1 1 10 0v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="waves-header-text">
            <h3 class="waves-dialog-title">Change Password</h3>
          </div>
        </div>
        <button @click="$emit('close')" class="waves-close-btn">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

      <div class="waves-dialog-body">
        <div class="waves-form-section">
          <div class="waves-form-group">
            <label class="waves-form-label"><span class="waves-label-text">Current Password</span></label>
            <div class="waves-input-container">
              <input v-model="oldPassword" type="password" class="waves-form-control" placeholder="Enter current password" @keyup.enter="submit" />
            </div>
          </div>

          <div class="waves-form-group">
            <label class="waves-form-label"><span class="waves-label-text">New Password</span></label>
            <div class="waves-input-container">
              <input v-model="newPassword" type="password" class="waves-form-control" placeholder="Enter new password" @keyup.enter="submit" />
            </div>
            <div class="waves-form-hint">At least 8 characters, include uppercase, lowercase and numbers.</div>
          </div>

          <div class="waves-form-group">
            <label class="waves-form-label"><span class="waves-label-text">Confirm New Password</span></label>
            <div class="waves-input-container">
              <input v-model="newPassword2" type="password" class="waves-form-control" placeholder="Re-enter new password" @keyup.enter="submit" />
            </div>
          </div>

          <div v-if="errorMessage" class="waves-form-error">
            <svg class="waves-error-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="waves-error-text">{{ errorMessage }}</span>
          </div>
          <div v-else-if="successMessage" class="waves-form-success">
            <svg class="waves-success-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="waves-success-text">{{ successMessage }}</span>
          </div>
        </div>
      </div>

      <div class="waves-dialog-footer">
        <button @click="$emit('close')" class="waves-btn waves-btn-secondary">Cancel</button>
        <button @click="submit" class="waves-btn waves-btn-primary" :disabled="submitting">{{ submitting ? 'Saving...' : 'Save New Password' }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { ref } from 'vue'

export default {
  name: 'ChangePasswordDialog',
  emits: ['close','success'],
  setup(props, { emit }) {
    const oldPassword = ref('')
    const newPassword = ref('')
    const newPassword2 = ref('')
    const submitting = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')

    const localValidate = () => {
      errorMessage.value = ''
      successMessage.value = ''
      if (!oldPassword.value || !newPassword.value || !newPassword2.value) {
        errorMessage.value = 'Please fill all fields'
        return false
      }
      if (newPassword.value !== newPassword2.value) {
        errorMessage.value = 'New passwords do not match'
        return false
      }
      // 简单复杂度提示；后端有强校验
      if (newPassword.value.length < 8) {
        errorMessage.value = 'Password must be at least 8 characters'
        return false
      }
      return true
    }

    const submit = async () => {
      if (submitting.value) return
      if (!localValidate()) return
      submitting.value = true
      try {
        const resp = await axios.post('/api/auth/change_password/', {
          old_password: oldPassword.value,
          new_password: newPassword.value,
          confirm_password: newPassword2.value,
        })
        successMessage.value = resp.data?.message || 'Password changed successfully'
        emit('success')
        setTimeout(() => emit('close'), 600)
      } catch (error) {
        const data = error.response?.data
        // 兼容各种后端错误格式
        const msg = Array.isArray(data) ? data[0] : (data?.detail || data?.message || data?.error || 'Password change failed')
        errorMessage.value = msg
      } finally {
        submitting.value = false
      }
    }

    return {
      oldPassword,
      newPassword,
      newPassword2,
      submitting,
      errorMessage,
      successMessage,
      submit,
    }
  }
}
</script>

<style scoped>
.waves-password-dialog {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.waves-dialog-container {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,.1), 0 10px 10px -5px rgba(0,0,0,.04);
  max-width: 500px;
  width: 90vw;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.waves-dialog-header { display:flex; align-items:center; justify-content:space-between; padding:1.25rem 1.75rem; border-bottom:1px solid #e5e7eb; }
.waves-header-content { display:flex; gap:.75rem; align-items:center; }
.waves-header-icon { width:36px; height:36px; color: var(--profile-primary); }
.waves-header-text .waves-dialog-title { margin:0; font-size:18px; font-weight:600; color:#323130; }
.waves-close-btn { background:transparent; border:none; cursor:pointer; color:#605e5c; }

.waves-dialog-body { padding:1.25rem 1.75rem; }
.waves-form-group { margin-bottom:1rem; }
.waves-form-label { font-size:14px; font-weight:500; color:#605e5c; margin-bottom:.25rem; display:block; }
.waves-input-container { position:relative; }
.waves-form-control { width:100%; padding:.5rem .75rem; border:1px solid #d1d5db; border-radius:8px; font-size:14px; }
.waves-form-hint { font-size:12px; color:#6b7280; margin-top:.25rem; }
.waves-form-error, .waves-form-success { display:flex; align-items:center; gap:.5rem; margin-top:.5rem; }
.waves-error-icon, .waves-success-icon { width:18px; height:18px; }
.waves-error-text { color:#b91c1c; font-size:13px; }
.waves-success-text { color:#166534; font-size:13px; }

.waves-dialog-footer { display:flex; justify-content:flex-end; gap:.5rem; padding:1rem 1.75rem; border-top:1px solid #e5e7eb; }
.waves-btn { display:inline-flex; align-items:center; gap:.5rem; padding:.5rem .75rem; border-radius:8px; border:1px solid transparent; font-size:14px; cursor:pointer; }
.waves-btn-primary { background: var(--profile-primary); color:#fff; }
.waves-btn-primary:hover { background: var(--profile-primary-hover); }
.waves-btn-secondary { background:#f3f4f6; color:#111827; }
</style>