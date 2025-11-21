<template>
  <div class="ms-profile-container">
    <div class="ms-profile-content">
      <!-- 简洁头部 -->
      <div class="ms-profile-header">
        <div class="ms-avatar">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12C14.7614 12 17 9.76142 17 7C17 4.23858 14.7614 2 12 2C9.23858 2 7 4.23858 7 7C7 9.76142 9.23858 12 12 12Z"/>
            <path d="M12 14C7.58172 14 4 17.5817 4 22H20C20 17.5817 16.4183 14 12 14Z"/>
          </svg>
        </div>
        <h1 class="ms-title">Profile</h1>
      </div>

      <div v-if="currentUser" class="ms-profile-body">
        <!-- 基本信息 -->
        <div class="ms-section">
          <h2 class="ms-section-title">Basic Information</h2>
          <div class="ms-info-list">
            <div class="ms-info-row">
              <span class="ms-label">Email Address</span>
              <span class="ms-value">{{ currentUser.email }}</span>
            </div>
            <div class="ms-info-row">
              <span class="ms-label">Registered At</span>
              <span class="ms-value">{{ formatDate(currentUser.date_joined) }}</span>
            </div>
            <div class="ms-info-row">
              <span class="ms-label">Last Login</span>
              <span class="ms-value">{{ formatDate(currentUser.last_login) }}</span>
            </div>
            <div class="ms-info-row" v-if="organizations && organizations.length">
              <span class="ms-label">Organizations</span>
              <div class="ms-value ms-org-list">
                <div class="ms-org-item" v-for="o in organizations" :key="o.id">
                  {{ o.name }}<span v-if="o.role" class="ms-org-role"> ({{ o.role }})</span>
                </div>
              </div>
            </div>
            <div class="ms-action-row">
              <button class="ms-action-btn" @click="openChangePassword">Change Password</button>
              <!-- 已移到导航栏，仅保留密码修改按钮 -->
            </div>
          </div>
        </div>
      </div>
      
      <!-- 加载状态 -->
      <div v-else class="ms-loading">
        <div class="ms-spinner"></div>
        <p>Loading user information...</p>
      </div>

      <!-- 修改密码弹窗 -->
      <ChangePasswordDialog v-if="showChangePassword" @close="closeChangePassword" @success="onPasswordChanged" />
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'
import ChangePasswordDialog from '../components/ChangePasswordDialog.vue'

export default {
  name: 'Profile',
  components: { ChangePasswordDialog },
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    
    const currentUser = computed(() => authStore.currentUser)
    const isSuperuser = computed(() => !!authStore.currentUser?.is_superuser)
    const organizations = ref([])
    
    const formatDate = (dateString) => {
      if (!dateString) return 'Unknown'
      return new Date(dateString).toLocaleString('en-US')
    }
    
    
    const handleLogout = async () => {
      await authStore.logout()
      router.push('/')
    }

    const goAdmin = () => {
      // 进入后端组织成员管理 UI（用户提供的目标端口与路径）
    // 通过前端代理到后端，避免跨域与外网端口直连导致的 502
    // 跳转到组织列表页，便于创建/管理组织
    const url = `/api/auth/orgs/ui/`
      window.location.href = url
    }

    const showChangePassword = ref(false)
    const openChangePassword = () => { showChangePassword.value = true }
    const closeChangePassword = () => { showChangePassword.value = false }
    const onPasswordChanged = () => {
      // 修改成功后刷新用户信息（防止服务端对安全字段有更新）
      authStore.fetchUser()
    }
    
    // 加载组织列表
    const fetchOrganizations = async () => {
      try {
        const token = localStorage.getItem('token')
        const headers = token ? { Authorization: `Token ${token}` } : {}
        const res = await axios.get('/api/auth/orgs/', { headers })
        organizations.value = res.data?.organizations || []
      } catch (e) {
        console.warn('获取组织列表失败：', e?.response?.status, e?.response?.data || e?.message)
        organizations.value = []
      }
    }

    onMounted(() => {
      fetchOrganizations()
    })
    
    return {
      currentUser,
      formatDate,
      handleLogout,
      isSuperuser,
      goAdmin,
      organizations,
      showChangePassword,
      openChangePassword,
      closeChangePassword,
      onPasswordChanged
    }
  }
}
</script>

<style scoped>
/* 微软风格个人资料页面 */
.ms-profile-container {
  min-height: 100vh;
  background: transparent; /* 与全局 body 背景一致，去掉外层矩形 */
  padding: 20px;
}

.ms-profile-content {
  width: 960px; /* 固定更宽的泡泡宽度 */
  max-width: 960px;
  margin: 0 auto;
  background: #fff;
  border-radius: 16px; /* 圆角气泡 */
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  /* 让页面各处可用统一主题色变量 */
  --profile-primary: rgb(58, 126, 185);
  --profile-primary-hover: rgb(45, 102, 150);
}

/* 头部样式 */
.ms-profile-header {
  background: white;
  padding: 16px 24px 12px; /* 降低整体高度 */
  display: flex;
  align-items: center;
  gap: 16px;
}

.ms-avatar {
  width: 48px;
  height: 48px;
  background: var(--profile-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.ms-avatar svg {
  width: 24px;
  height: 24px;
}

.ms-title {
  font-size: 24px;
  font-weight: 600;
  color: #323130;
  margin: 0;
  line-height: 1.2;
}

/* 主体内容 */
.ms-profile-body {
  padding: 0;
}

.ms-section {
  padding: 16px 24px; /* 降低整体高度 */
}

.ms-section-title {
  font-size: 18px;
  font-weight: 600;
  color: #323130;
  margin: 0 0 16px 0;
  line-height: 1.3;
}

/* 信息列表 */
.ms-info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ms-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0; /* 降低整体高度 */
  min-height: 28px;
}

.ms-label {
  font-size: 14px;
  font-weight: 500;
  color: #605e5c;
  flex-shrink: 0;
  width: 120px;
}

.ms-value {
  font-size: 14px;
  color: #323130;
  text-align: right;
  word-break: break-all;
  flex: 1;
}

/* 组织列表纵向排列，左对齐显示 */
.ms-org-list {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ms-org-item {
  line-height: 1.4;
}
.ms-org-role {
  color: #605e5c;
}

.ms-action-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.ms-action-btn {
  background: var(--profile-primary);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
}

.ms-action-btn:hover {
  background: var(--profile-primary-hover);
}

.ms-admin-btn {
  margin-left: 8px; /* 仅用于与前一个按钮间隔，样式继承 ms-action-btn */
}


/* 统计网格 */
.ms-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.ms-stat-item {
  background: #ffffff; /* 纯白背景，去掉灰边视觉 */
  border-radius: var(--waves-radius-sm);
  padding: 16px;
  text-align: center;
  border-top: 2px solid var(--profile-primary);
}

.ms-stat-number {
  font-size: 28px;
  font-weight: 600;
  color: var(--profile-primary);
  margin-bottom: 4px;
  line-height: 1.2;
}

.ms-stat-label {
  font-size: 12px;
  color: #605e5c;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 加载状态 */
.ms-loading {
  text-align: center;
  padding: 48px 32px;
}

.ms-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #edebe9;
  border-top: 2px solid var(--profile-primary);
  border-radius: 50%;
  animation: ms-spin 1s linear infinite;
  margin: 0 auto 16px;
}

.ms-loading p {
  font-size: 14px;
  color: #605e5c;
  margin: 0;
}

@keyframes ms-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .ms-profile-container {
    padding: 16px;
  }
  .ms-profile-content {
    width: 100%; /* 小屏等比收缩 */
    max-width: 100%;
  }
  
  .ms-profile-header {
    padding: 20px 24px 12px;
  }
  
  .ms-section {
    padding: 20px 24px;
  }
  
  .ms-title {
    font-size: 20px;
  }
  
  .ms-info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .ms-label {
    width: auto;
  }
  
  .ms-value {
    text-align: left;
  }
  
  .ms-stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .ms-profile-container {
    padding: 12px;
  }
  .ms-profile-content {
    width: 100%;
    max-width: 100%;
  }
  
  .ms-profile-header {
    padding: 16px 20px 8px;
    gap: 12px;
  }
  
  .ms-avatar {
    width: 40px;
    height: 40px;
  }
  
  .ms-avatar svg {
    width: 20px;
    height: 20px;
  }
  
  .ms-title {
    font-size: 18px;
  }
  
  .ms-section {
    padding: 16px 20px;
  }
  
  .ms-section-title {
    font-size: 16px;
  }
  
  .ms-stat-item {
    padding: 12px;
  }
  
  .ms-stat-number {
    font-size: 24px;
  }
}
</style>
