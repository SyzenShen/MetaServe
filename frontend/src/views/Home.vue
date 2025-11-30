<template>
  <div class="waves-corporate-bg home-bleed" :class="{ 'unauth-bg': !isAuthenticated }">
    <!-- Semi-transparent right-side overlay for unauthenticated welcome page -->
    <div v-if="!isAuthenticated" class="unauth-overlay"></div>
    <!-- 壁纸左上角的品牌标识（未登录时显示） -->
    <div v-if="!isAuthenticated" class="wallpaper-brand">
      <img :src="logoSrc" alt="MetaServe Logo" class="wallpaper-logo" @error="handleLogoError" />
      <span class="wallpaper-title">MetaServe</span>
    </div>
    <div class="page-center container">
      <section v-if="!isAuthenticated" class="unauth-layout">
        <!-- 左侧品牌卡片：MetaServe, Simple. Secure. Smart. -->
        <div class="unauth-left">
          <div class="brand-card">
            <h1 class="brand-title">MetaServe</h1>
            <p class="brand-subtitle">MetaServe is a lightweight, metadata-aware layer for discovering and delivering institutional biomedical files. It offers faceted search over curated metadata and audited, zero-copy handoff from data at rest to visualization and HPC workflows.</p>
            <p class="brand-meta">
              Open-source (MIT). Source code and docs at:
              <a href="https://github.com/SyzenShen/Download_system_project" target="_blank" rel="noopener" class="brand-link">
                <code>https://github.com/SyzenShen/Download_system_project</code>
              </a>
            </p>
          </div>
        </div>

        <!-- 右侧登录/注册切换面板 -->
        <div class="unauth-right">
          <div class="card page-card waves-auth-card waves-well auth-card">
            <div class="card-header waves-auth-header">
              <h2 class="card-title waves-text-corporate">{{ activeAuth === 'login' ? 'User Login' : 'User Registration' }}</h2>
              <p class="waves-text-light">{{ activeAuth === 'login' ? 'Sign in to your account' : 'Create your account' }}</p>
            </div>
            <div class="card-body waves-auth-body">
              <!-- 错误与成功提示 -->
              <div v-if="error" class="alert alert-error waves-alert-error">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2C6.48 2 2 6.48 2 12S6.48 22 12 22 22 17.52 22 12 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z" fill="currentColor"/>
                </svg>
                {{ error }}
              </div>
              <div v-if="activeAuth === 'register' && successMessage" class="alert alert-success waves-alert-success">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" fill="currentColor"/>
                </svg>
                {{ successMessage }}
              </div>

              <!-- 登录表单 -->
              <form v-if="activeAuth === 'login'" @submit.prevent="handleLogin" class="waves-auth-form">
                <div class="form-group waves-form-group">
                  <label for="login_email" class="form-label waves-form-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M20 4H4C2.9 4 2.01 4.9 2.01 6L2 18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V6C22 4.9 21.1 4 20 4ZM20 8L12 13L4 8V6L12 11L20 6V8Z" fill="currentColor"/>
                    </svg>
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="login_email"
                    v-model="loginForm.email"
                    class="form-control waves-form-control"
                    placeholder="Enter your email address"
                    required
                    :disabled="isLoading"
                  />
                </div>

                <div class="form-group waves-form-group">
                  <label for="login_password" class="form-label waves-form-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M18 8H17V6C17 3.24 14.76 1 12 1S7 3.24 7 6V8H6C4.9 8 4 8.9 4 10V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V10C20 8.9 19.1 8 18 8ZM12 17C10.9 17 10 16.1 10 15S10.9 13 12 13 14 13.9 14 15 13.1 17 12 17ZM15.1 8H8.9V6C8.9 4.29 10.29 2.9 12 2.9S15.1 4.29 15.1 6V8Z" fill="currentColor"/>
                    </svg>
                    Password
                  </label>
                  <input
                    type="password"
                    id="login_password"
                    v-model="loginForm.password"
                    class="form-control waves-form-control"
                    placeholder="Enter your password"
                    required
                    :disabled="isLoading"
                  />
                </div>

                <div class="form-group waves-submit-group">
                  <button type="submit" class="btn btn-primary waves-btn waves-btn-primary auth-submit-center" :disabled="isLoading">
                    <span v-if="isLoading" class="waves-loading-spinner"></span>
                    {{ isLoading ? 'Signing in...' : 'Sign In' }}
                  </button>
                </div>
              </form>

              <!-- 注册表单 -->
              <form v-else @submit.prevent="handleRegister" class="waves-auth-form waves-register-form">
                <div class="form-group waves-form-group">
                  <label for="reg_email" class="form-label waves-form-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M20 4H4C2.9 4 2.01 4.9 2.01 6L2 18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V6C22 4.9 21.1 4 20 4ZM20 8L12 13L4 8V6L12 11L20 6V8Z" fill="currentColor"/>
                    </svg>
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="reg_email"
                    v-model="registerForm.email"
                    class="form-control waves-form-control"
                    placeholder="Enter your email address"
                    required
                    :disabled="isLoading"
                  />
                </div>

                <div class="form-group waves-form-group">
                  <label for="reg_password" class="form-label waves-form-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M18 8H17V6C17 3.24 14.76 1 12 1S7 3.24 7 6V8H6C4.9 8 4 8.9 4 10V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V10C20 8.9 19.1 8 18 8ZM12 17C10.9 17 10 16.1 10 15S10.9 13 12 13 14 13.9 14 15 13.1 17 12 17ZM15.1 8H8.9V6C8.9 4.29 10.29 2.9 12 2.9S15.1 4.29 15.1 6V8Z" fill="currentColor"/>
                    </svg>
                    Password
                  </label>
                  <input
                    type="password"
                    id="reg_password"
                    v-model="registerForm.password"
                    class="form-control waves-form-control"
                    :class="{ 'waves-form-error': registerForm.password && !isPasswordValid }"
                    placeholder="Enter a password"
                    required
                    :disabled="isLoading"
                    minlength="8"
                    @input="validatePassword"
                  />
                </div>

                <div class="form-group waves-form-group">
                  <label for="reg_confirm" class="form-label waves-form-label">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z" fill="currentColor"/>
                    </svg>
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    id="reg_confirm"
                    v-model="registerForm.confirmPassword"
                    class="form-control waves-form-control"
                    :class="{ 'waves-form-error': registerForm.password && registerForm.confirmPassword && registerForm.password !== registerForm.confirmPassword }"
                    placeholder="Re-enter your password"
                    required
                    :disabled="isLoading"
                  />
                  <small v-if="registerForm.password && registerForm.confirmPassword && registerForm.password !== registerForm.confirmPassword" class="waves-form-error-text">
                    Passwords do not match
                  </small>
                </div>

                <div class="form-group waves-submit-group">
                  <button type="submit" class="btn btn-primary waves-btn waves-btn-primary" :disabled="isLoading || registerForm.password !== registerForm.confirmPassword || !isPasswordValid">
                    <span v-if="isLoading" class="waves-loading-spinner"></span>
                    {{ isLoading ? 'Registering...' : 'Sign Up' }}
                  </button>
                </div>
              </form>

              <div class="waves-auth-footer">
                <div class="waves-divider">
                  <span class="waves-divider-text">or</span>
                </div>
                <p class="waves-text-light">
                  {{ activeAuth === 'login' ? "Don't have an account?" : 'Already have an account?' }}
                  <a href="#" class="waves-link" @click.prevent="toggleAuth">
                    {{ activeAuth === 'login' ? 'Sign Up' : 'Sign In' }}
                  </a>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div v-else class="card page-card hero-card waves-well">
        <div class="card-body">
        <div class="insight-card headline-card">
          <div class="headline-content">
            <img src="./logo.png" alt="MetaServe Logo" class="hero-logo" />
            <h1 class="card-title title-stable waves-text-corporate hero-title">MetaServe</h1>
            
            <h3 v-if="isAuthenticated" class="headline-welcome waves-text-corporate">Welcome back, {{ currentUser?.username || 'User' }}!</h3>
          </div>
          <div v-if="isAuthenticated" class="headline-actions">
            <router-link to="/files" class="btn btn-primary waves-btn insight-btn">View My Files</router-link>
          </div>
        </div>
        
        <div class="dashboard-section">
          
          <div class="home-insights two-col" v-if="statsReady">
            <div class="insights-tiles">
              <div class="insight-card">
                <div class="insight-value">{{ totalFiles }}</div>
                <div class="insight-label">Total Files</div>
                <p class="insight-caption">Count of all files in your storage.</p>
              </div>
              <div class="insight-card">
                <div class="insight-value">{{ totalFolders }}</div>
                <div class="insight-label">Total Folders</div>
                <p class="insight-caption">Organize your data with nested folders.</p>
              </div>
              <div class="insight-card highlight">
                <div class="insight-value">{{ formattedTotalSize }}</div>
                <div class="insight-label">Total Size</div>
                <p class="insight-caption">Aggregated size of all files.</p>
              </div>
              <div class="insight-card">
                <div class="insight-value">{{ formattedQuota }}</div>
                <div class="insight-label">Total Quota</div>
                <p class="insight-caption">Account storage quota.</p>
              </div>
            </div>
            <div class="insights-right">
              <div class="insight-card pie-card">
                <StoragePie :used-bytes="totalSizeBytes" :quota-bytes="quotaBytes" />
              </div>
            </div>
          </div>
          

        </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useFilesStore } from '../stores/files'
import StoragePie from '../components/StoragePie.vue'
import assetLogo from '../assets/images/logo.png'

export default {
  name: 'Home',
  components: { StoragePie },
  setup() {
    const authStore = useAuthStore()
    const filesStore = useFilesStore()
    const isAuthenticated = computed(() => authStore.isAuthenticated)
    const currentUser = computed(() => authStore.currentUser)
    const statsReady = ref(false)

    // 未登录右侧内嵌登录/注册表单的状态与逻辑
    const activeAuth = ref('login') // 'login' | 'register'
    const toggleAuth = () => { activeAuth.value = activeAuth.value === 'login' ? 'register' : 'login' }
    const isLoading = computed(() => authStore.isLoading)
    const error = computed(() => authStore.error)

    // 登录表单
    const loginForm = ref({ email: '', password: '' })
    const handleLogin = async () => {
      const result = await authStore.login(loginForm.value)
      if (result.success) {
        // 登录成功后直接进入首页（此组件会切换到已登录视图）
        activeAuth.value = 'login'
      }
    }

    // 注册表单
    const registerForm = ref({ email: '', password: '', confirmPassword: '' })
    const successMessage = ref('')
    const passwordChecks = ref({ length: false, uppercase: false, lowercase: false, number: false })
    const isPasswordValid = computed(() => passwordChecks.value.length && passwordChecks.value.uppercase && passwordChecks.value.lowercase && passwordChecks.value.number)
    const validatePassword = () => {
      const password = registerForm.value.password || ''
      passwordChecks.value.length = password.length >= 8
      passwordChecks.value.uppercase = /[A-Z]/.test(password)
      passwordChecks.value.lowercase = /[a-z]/.test(password)
      passwordChecks.value.number = /\d/.test(password)
    }
    const handleRegister = async () => {
      if (registerForm.value.password !== registerForm.value.confirmPassword) return
      const result = await authStore.register({
        email: registerForm.value.email,
        password: registerForm.value.password,
        confirm_password: registerForm.value.confirmPassword,
      })
      if (result.success) {
        successMessage.value = result.message
        // 注册成功后切换到登录页表单
        setTimeout(() => { activeAuth.value = 'login' }, 1500)
      }
    }

    const totalFiles = computed(() => filesStore.files.length)
    const totalFolders = computed(() => filesStore.folders.length)
    const totalSizeBytes = computed(() => filesStore.files.reduce((sum, f) => sum + (f.file_size || 0), 0))
    const formattedTotalSize = computed(() => {
      const bytes = totalSizeBytes.value
      if (!bytes) return '0 B'
      const units = ['B', 'KB', 'MB', 'GB', 'TB']
      const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
      const value = bytes / Math.pow(1024, exponent)
      return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`
    })

    const formattedQuota = computed(() => {
      const defaultQuota = 50 * 1024 * 1024 * 1024
      const quotaBytes = currentUser.value?.storage_quota ?? defaultQuota
      const quotaGB = quotaBytes / (1024 * 1024 * 1024)
      return `${quotaGB % 1 === 0 ? quotaGB : quotaGB.toFixed(1)} GB`
    })
    const quotaBytes = computed(() => currentUser.value?.storage_quota ?? (50 * 1024 * 1024 * 1024))

    const initStats = async () => {
      try { await filesStore.fetchFiles(null) } catch (_) {}
      statsReady.value = true
    }

    onMounted(async () => {
      if (isAuthenticated.value) {
        await initStats()
      }
    })

    watch(isAuthenticated, async (val) => {
      if (val) {
        await initStats()
      }
    })

    // 未登录首页品牌标识的 logo 资源与降级处理
    const logoSrc = ref('/api/auth/logo.png')
    const handleLogoError = () => { logoSrc.value = assetLogo }
    
    return {
      isAuthenticated,
      currentUser,
      statsReady,
      totalFiles,
      totalFolders,
      formattedTotalSize
      , formattedQuota,
      totalSizeBytes,
      quotaBytes,
      // 未登录内嵌认证面板暴露变量/方法
      activeAuth,
      toggleAuth,
      isLoading,
      error,
      loginForm,
      handleLogin,
      registerForm,
      successMessage,
      passwordChecks,
      isPasswordValid,
      validatePassword,
      handleRegister
      , logoSrc, handleLogoError
    }
  }
}

</script>
<style scoped>
.unauth-layout {
  position: relative;
  display: grid;
  grid-template-columns: 1fr clamp(380px, 32vw, 480px);
  align-items: center;
  justify-items: center; /* 两列内容在各自列水平居中 */
  min-height: 100vh; /* 以视口高度为基准垂直居中 */
  gap: 0;
}
.unauth-left {
  display: flex;
  align-items: center;
  justify-self: start;
  padding-left: min(2vw, 40px);
}
.brand-card {
  /* 深色玻璃态背景，保留模糊效果 */
  background: rgba(12, 22, 34, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 12px;
  padding: 36px 44px;
  box-shadow: 0 6px 22px rgba(0,0,0,0.12);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  max-width: 800px;
  transform: translate(-320px, -60px);
}
.brand-title { font-size: 3.8rem; font-weight: 700; margin-bottom: 22px; color: #ffffff; text-shadow: 0 0 10px rgba(255, 255, 255, 0.18); }
.brand-subtitle { font-size: 1rem; margin: 0; color: #e5e5e5; text-shadow: 0 0 6px rgba(255, 255, 255, 0.16); }
/* 开源提示与链接 */
.brand-meta { margin-top: 14px; font-size: 0.95rem; color: #e8eef6; }
.brand-link { color: #ffffff; text-decoration: none; }
.brand-link code { color: #ffffff; background: rgba(255, 255, 255, 0.12); padding: 2px 6px; border-radius: 4px; }

.unauth-right {
  position: relative;
  display: flex;
  align-items: center; /* 垂直居中到右侧遮罩内 */
  justify-content: center;
  padding: 0 24px 0 0; /* 略增右侧外边距，避免贴边拥挤 */
}
/* 将右侧注册卡宽度与遮罩列一致，提升输入框可用宽度 */
.auth-card { transform: translateY(-40px); width: clamp(380px, 32vw, 480px); }
/* Dark glass style for right-side auth card on unauth layout */
.unauth-right .auth-card {
  background: rgba(12, 22, 34, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  box-shadow: 0 8px 30px rgba(12, 22, 34, 0.25);
}
.unauth-right .waves-auth-header,
.unauth-right .waves-auth-body,
.unauth-right .waves-auth-footer {
  background: transparent;
}
/* 降低卡片内部左右内边距，扩大输入框视觉宽度 */
.unauth-right .waves-auth-body { padding: 36px 32px; }
/* Center the Sign In button within submit group */
.unauth-right .waves-submit-group { display: flex; justify-content: center; }
.unauth-right .auth-submit-center { margin: 0 auto; display: inline-flex; }
/* 注册页输入框与登录页一致：占满容器宽度 */
.waves-register-form .waves-form-control { width: 100% !important; }

/* 覆盖右侧面板内文本颜色为白色，提升对比度 */
.unauth-right .waves-auth-header .card-title { color: #ffffff !important; font-size: 2rem; }
.unauth-right .waves-auth-header .card-title.waves-text-corporate { color: #ffffff !important; }
.unauth-right .waves-auth-header p { color: #e5e5e5; }
.unauth-right .waves-form-label { color: #ffffff; }
.unauth-right .waves-divider { color: #e5e5e5; }
.unauth-right .waves-link { color: #ffffff; }
/* 统一页脚提示文字为白色 */
.unauth-right .waves-auth-footer p,
.unauth-right .waves-text-light,
.unauth-right .waves-divider-text { color: #ffffff; }
/* Make footer inline: "or Don't have an account? Sign Up" in one line */
.unauth-right .waves-auth-footer { text-align: center; }
.unauth-right .waves-auth-footer .waves-divider { margin: 10px 0; }
.unauth-right .waves-auth-footer p { display: inline-block; margin-top: 0; }
.unauth-right .waves-auth-footer .waves-divider-text { display: inline; margin: 0 8px; }
.unauth-right .waves-auth-footer .waves-link { display: inline; }

.unauth-overlay {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: clamp(380px, 32vw, 480px);
  background: rgba(12, 22, 34, 0.32);
  border-left: 1px solid rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 0 !important; /* ensure it sits below content */
  pointer-events: none; /* avoid intercepting clicks */
}


.waves-corporate-bg {
  /* Disable corporate banner image and overlay for Home */
  --waves-banner-image: none !important;
  --waves-corporate-overlay: transparent !important;
  background: var(--waves-corporate-gradient) !important;
  /* Ensure no internal overlay layers from global styles interfere */
  isolation: isolate;
}

/* Make the corporate background span full viewport width to eliminate white side edges */
.home-bleed {
  position: relative;
  left: 50%;
  right: 50%;
  margin-left: -50vw;
  margin-right: -50vw;
  width: 100vw;
  box-sizing: border-box;
  overflow-x: hidden;
  /* Avoid unintended clipping or masks */
  background-clip: border-box;
}

/* 未登录时使用 image.png 作为背景 */
.home-bleed.unauth-bg {
  background: url('./image.png') center/cover no-repeat !important;
}

/* 让首页容器占满视口并取消居中，仅在未登录视图生效 */
.home-bleed.unauth-bg :global(.page-center.container) {
  max-width: none !important;
  width: 100vw !important;
  margin: 0 !important;
  /* 去掉顶部内边距，让背景贴紧导航栏 */
  padding-top: 0 !important;
  /* 未登录首页需要满屏贴顶，忽略全局 100vh - 72px */
  min-height: 100vh !important;
}

/* 未登录首页裁掉页面最上方20px不可见区域（配合 App.vue 的 home-top-crop 类） */
:global(main.container.home-top-crop) {
  position: relative;
  top: -25px;             /* 向上位移 20px，裁掉顶部 */
  padding-top: 20px;      /* 回补内容布局，避免被压到视口外 */
}

/* 仅在未登录视图统一容器内边距，贴右侧容器 */
.home-bleed.unauth-bg .page-center.container {
  /* 顶部 0；右侧贴边 0；底部 24px（保持下方适度空间） */
  padding: 0 0 24px !important;
  align-items: flex-start;
  justify-content: flex-end !important;
}

/* 壁纸上的品牌标识（左上角叠加） */
.wallpaper-brand {
  position: absolute;
  top: 14px;
  left: min(2vw, 20px);
  display: inline-flex;
  align-items: center;
  gap: 10px;
  z-index: 2;
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
}
.wallpaper-logo { height: 36px; width: auto; }
.wallpaper-title {
  font-size: 22px;
  font-weight: 700;
  color: #000000;
  text-shadow: none;
}

.home-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.hero-card {
  max-width: 1200px !important;
  width: 100%;
  text-align: center;
  padding: 32px;
  border-radius: var(--radius-lg);
  /* Remove any container-level mask/clipping so inner cards' shadows show fully */
  overflow: visible !important;
  /* neutralize decorative background/shadow to avoid perceived side obstructions */
  background: transparent !important;
  backdrop-filter: none !important;
  border: none !important;
  box-shadow: none !important;
  margin: -12px auto 0; /* 整体轻微上移 */
}

/* Plan A: make the hero container transparent and remove blur when using waves-well */
.hero-card.waves-well {
  background: transparent !important;
  padding: 0 !important;
  backdrop-filter: none !important;
  box-shadow: none !important;
  border: none !important;
}

.hero-title {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 18px;
  color: #1a1a1a;
  line-height: 1.2;
}

.hero-logo { width: 80px; height: auto; margin-bottom: -8px; display: inline-block; }

.hero-subtitle {
  font-size: 1.2rem;
  margin-bottom: 24px;
  color: #666666;
  font-weight: 400;
  line-height: 1.4;
}

.section-title {
  font-size: 1.8rem;
  font-weight: 600;
  margin-bottom: 24px;
  color: var(--waves-text-corporate);
}

.welcome-section,
.dashboard-section {
  margin-bottom: 40px;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin: 32px 0;
}

.waves-btn {
  padding: 6px 28px;
  border-radius: var(--waves-radius-sm);
  text-decoration: none;
  font-weight: 600;
  font-size: 1rem;
  transition: all 0.3s ease;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
  justify-content: center;
}

.btn-primary.waves-btn {
  background: rgb(58, 126, 185);
  color: #ffffff;
  border: none;
  box-shadow: 0 2px 4px rgba(58, 126, 185, 0.3);
}

.btn-primary.waves-btn:hover {
  background: rgb(45, 102, 150);
  color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(45, 102, 150, 0.4);
}

.btn-secondary.waves-btn {
  background: transparent;
  color: rgb(58, 126, 185);
  border: 2px solid rgb(58, 126, 185);
  box-shadow: 0 2px 4px rgba(58, 126, 185, 0.3);
}

.btn-secondary.waves-btn:hover {
  background: rgb(58, 126, 185);
  color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(58, 126, 185, 0.4);
}

.btn-success.waves-btn {
  background: var(--waves-success);
  color: white;
  box-shadow: var(--waves-shadow-md);
}

.btn-success.waves-btn:hover {
  background: var(--waves-success-hover);
  transform: translateY(-2px);
  box-shadow: var(--waves-shadow-lg);
}

.btn-icon {
  font-size: 1.1rem;
}

.features-preview {
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--waves-border-color);
}

/* Home insights cards */
.home-insights {
  margin-top: 8px; /* 缩小标题与网格之间的距离 */
  display: grid;
  gap: 16px;
  width: 100%;
  /* Widen to align with headline card width */
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.home-insights.two-col {
  grid-template-columns: 1fr 360px;
  align-items: start;
  justify-content: center;
  gap: 16px; /* 统一列与行间距为 16px */
}

.insights-tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 16px;
}

/* Center text within the statistic tiles */
.insights-tiles .insight-card {
  text-align: center;
  padding-top: 47px; /* move value and texts down */
}

.insights-right {
  display: flex;
  /* Stretch to match the left tiles column height for alignment */
  align-self: stretch;
}
.pie-card {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  /* Make the Storage Usage card taller to visually align with left cards */
  height: 100%;
  min-height: 420px;
}
.pie-card canvas { max-width: 100%; height: auto; }

.insight-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 26px 28px;
  box-shadow: 0 12px 30px rgba(27, 44, 72, 0.08);
  min-height: 200px;
}

.headline-card {
  /* Wider and aligned with the insights grid below */
  max-width: 1200px !important;
  width: 100%;
  margin: 0 auto; /* 去除额外下边距，统一用行间距控制 */
  padding: 40px 0; /* remove horizontal padding for alignment */
  min-height: 200px;
  text-align: left; /* override hero-card center */
}
.headline-card {
  display: grid;
  grid-template-columns: 1fr 360px; /* match insights grid right column */
  align-items: center;
  column-gap: 24px; /* match grid gap */
}

/* 统一页面主体内的上下块间距，确保各块等距 */
.card.page-card.hero-card .card-body {
  display: grid;
  row-gap: 12px; /* 进一步压缩块与块之间的垂直间距 */
}
.headline-content { padding-left: 32px; }
.headline-actions { display: flex; justify-content: flex-end; padding-right: 120px; }
.headline-actions .insight-btn { padding: 8px 16px; }
.headline-card .hero-title,
.headline-card .hero-subtitle,
.headline-card .headline-welcome {
  text-align: left;
  margin-left: 0;
}
.headline-card .hero-subtitle { margin-bottom: 0; }
.headline-card .headline-welcome { margin-top: 0; }
.headline-welcome {
  margin-top: 8px;
}

.insight-value {
  font-size: 28px;
  font-weight: 700;
  color: rgb(58, 126, 185);
}

.insight-label {
  font-size: 13px;
  color: var(--waves-text-light);
}

.insight-caption {
  font-size: 12px;
  color: var(--waves-text-light);
  line-height: 1.6;
  margin: 0;
}

.insight-actions { margin-top: 14px; }
.insight-btn { min-width: auto; padding: 4px 14px; font-size: 0.9rem; }

.features-preview h4 {
  font-size: 1.4rem;
  font-weight: 600;
  margin-bottom: 24px;
  color: var(--waves-text-corporate);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-top: 24px;
}

.feature-item {
  background: var(--waves-card-secondary-bg);
  padding: 24px;
  border-radius: var(--waves-border-radius);
  border: var(--waves-border-subtle);
  transition: all 0.3s ease;
}

.feature-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--waves-shadow-lg);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 16px;
}

.feature-item h5 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--waves-text-corporate);
}

.feature-item p {
  font-size: 0.9rem;
  color: var(--waves-text-light);
  margin: 0;
  line-height: 1.5;
}



.lead {
  font-size: 1.1rem;
  margin-bottom: 24px;
  color: var(--waves-text-light);
  line-height: 1.6;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .insight-card { min-height: auto; padding: 18px 20px; }
  .hero-card {
    padding: 32px 24px;
  }
  
  .hero-title {
    font-size: 2.2rem;
  }
  
  .hero-subtitle {
    font-size: 1.1rem;
  }
  
  .action-buttons {
    flex-direction: column;
    align-items: center;
  }
  
  .waves-btn {
    width: 100%;
    max-width: 280px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
  }
  .home-insights.two-col { grid-template-columns: 1fr; }
  .insights-tiles { grid-template-columns: 1fr; }
}

@media (max-width: 480px) {
  .home-container {
    padding: 16px;
  }
  
  .hero-card {
    padding: 24px 16px;
  }
  
  .hero-title {
    font-size: 1.8rem;
  }
}
</style>




