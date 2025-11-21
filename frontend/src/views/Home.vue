<template>
  <div class="waves-corporate-bg home-bleed">
    <div class="page-center container">
      <section v-if="!isAuthenticated" class="portal-unauth">
        <img src="./logo.png" alt="MetaServe Logo" class="portal-logo" />
        <h1 class="portal-title">MetaServe</h1>
        <p class="portal-subtitle">Simple. Secure. Smart.</p>
  <div class="portal-actions">
    <router-link to="/login" class="portal-link portal-link--signin">
      <span>Sign In</span>
    </router-link>
    <span class="portal-hint">
      <span>No account?</span>
      <router-link to="/register" class="portal-link portal-link--register"><span>Create one</span></router-link>
    </span>
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
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useFilesStore } from '../stores/files'
import StoragePie from '../components/StoragePie.vue'

export default {
  name: 'Home',
  components: { StoragePie },
  setup() {
    const authStore = useAuthStore()
    const filesStore = useFilesStore()
    const isAuthenticated = computed(() => authStore.isAuthenticated)
    const currentUser = computed(() => authStore.currentUser)
    const statsReady = ref(false)

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

    onMounted(async () => {
      if (isAuthenticated.value) {
        try { await filesStore.fetchFiles(null) } catch (_) {}
        statsReady.value = true
      }
    })
    
    return {
      isAuthenticated,
      currentUser,
      statsReady,
      totalFiles,
      totalFolders,
      formattedTotalSize
      , formattedQuota,
      totalSizeBytes,
      quotaBytes
    }
  }
}

</script>
<style scoped>
.portal-unauth {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 28px 20px;
  margin-top: -36px; /* 再上移一点 */
}
.portal-title { font-size: 3.2rem; font-weight: 700; margin-bottom: 6px; color: #1a1a1a; text-shadow: 0 0 8px rgba(58, 126, 185, 0.15); }
.portal-logo { width: 260px; height: auto; margin-bottom: 6px; display: inline-block; filter: drop-shadow(0 0 8px rgba(58, 126, 185, 0.25)); transition: filter 0.2s ease; }
.portal-logo:hover { filter: drop-shadow(0 0 12px rgba(58, 126, 185, 0.35)); }
.portal-subtitle { font-size: 1rem; margin-bottom: 24px; color: #666; text-shadow: 0 0 6px rgba(58, 126, 185, 0.12); }
  .portal-actions { display: flex; flex-direction: column; gap: 24px; align-items: flex-start; justify-content: center; margin-top: 38px; text-align: left; }
  /* 让 Sign In 居中 */
  .portal-actions .portal-link--signin { align-self: center; }
.portal-hint { color: #4a4a4a; font-size: 1rem; display: inline-flex; align-items: center; gap: 8px; }
.portal-secondary { color: rgb(58, 126, 185); text-decoration: none; font-weight: 600; }
/* Make Sign In button text larger only on the unauthenticated view */
.portal-actions .btn-primary.waves-btn { font-size: 1.2rem; }

/* Text link style for Sign In / Create one */
.portal-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #1a1a1a;
  font-weight: 600;
  text-decoration: none;
  padding-bottom: 2px;
  border-bottom: 2px solid transparent;
  transition: color 0.2s ease, border-color 0.2s ease;
}
.portal-icon svg { display: block; width: 14px; height: 14px; }

/* Sign In 专属样式：加粗、稍大、居中、悬停下划线与轻微变色 */
.portal-link--signin {
  font-weight: 700;
  font-size: 1.2rem;
  align-self: center;
  background: rgb(75, 126, 180); /* 深蓝 24 50 80 */
  color: #ffffff; /* 文本改为黑色 */
  border-radius: 4px;
  padding: 16px 28px; /* 纵向稍增，按钮更大一点 */
  border: 1px solid rgba(0, 0, 0, 0.15); /* 简洁描边 */
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06); /* 轻阴影，提升质感 */
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  border-bottom: none !important; /* 覆盖通用链接底线 */
}
.portal-link--signin:hover {
  background: rgb(45, 102, 150); /* 与主按钮悬停一致 */
  color: #fff !important; /* 悬停改为白字，提升对比 */
  border-bottom-color: transparent !important; /* 不显示底部线 */
  border-color: rgb(45, 102, 150); /* 与主按钮悬停一致 */
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12); /* 悬停阴影略增强 */
}
.portal-link:hover {
  color: rgb(58, 126, 185);
  border-bottom-color: rgb(58, 126, 185);
}
/* Register 悬停色与按钮保持一致 */
.portal-link--register:hover {
  color: rgb(45, 102, 150);
  border-bottom-color: rgb(45, 102, 150);
}
/* Active state highlight for current page link */
.portal-link.router-link-active,
.portal-link.router-link-exact-active {
  color: rgb(58, 126, 185);
  border-bottom-color: rgb(58, 126, 185);
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

/* Ensure container on Home page is not capped by global 1200px */
:global(.page-center.container) {
  max-width: 1060px !important;
  width: 100%;
  /* 减少首页的上页边距 */
  padding-top: 16px !important;
}

/* 仅在首页提升选择器权重并统一容器内边距，确保上移有效 */
.home-bleed .page-center.container {
  /* 顶部改为 0；左右保持 20px；底部 24px */
  padding: 0 20px 24px !important;
  align-items: flex-start;
}

.home-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.hero-card {
  max-width: 2000px !important;
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
  max-width: 2000px;
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
  max-width: 2000px !important;
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




