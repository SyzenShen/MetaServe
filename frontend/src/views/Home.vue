<template>
  <div class="waves-corporate-bg home-bleed">
    <div class="page-center container">
      <div class="card page-card hero-card waves-well">
        <div class="card-header" style="text-align: center;">
          <h1 class="card-title title-stable waves-text-corporate hero-title">BioFileManager</h1>
          <p class="waves-text-light hero-subtitle">Upload, organize and manage your files with ease</p>
        </div>
        <div class="card-body">
        
        
        <div v-if="!isAuthenticated" class="welcome-section">
          <h3 class="waves-text-corporate section-title">Get Started</h3>
          <div class="action-buttons">
            <router-link to="/login" class="btn btn-primary waves-btn">Sign In</router-link>
            <router-link to="/register" class="btn btn-secondary waves-btn">Create Account</router-link>
          </div>

        </div>
        
        <div v-else class="dashboard-section">
          <h3 class="waves-text-corporate section-title">Welcome back, {{ currentUser?.username || 'User' }}!</h3>
          
          <div class="action-buttons">
            <router-link to="/files" class="btn btn-primary waves-btn">
              View My Files
            </router-link>
            <router-link to="/search" class="btn btn-secondary waves-btn">
              Search Files
            </router-link>
          </div>
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

.home-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.hero-card {
  max-width: 1100px;
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
  margin: 0 auto;
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
  margin-bottom: 12px;
  color: #1a1a1a;
  line-height: 1.2;
}

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
  margin-top: 24px;
  display: grid;
  gap: 16px;
  width: 100%;
  max-width: 1000px;
  margin-left: auto;
  margin-right: auto;
}

.home-insights.two-col {
  grid-template-columns: 1fr 360px;
  align-items: start;
  justify-content: center;
  gap: 24px;
}

.insights-tiles {
  display: grid;
  grid-template-columns: repeat(2, minmax(240px, 1fr));
  gap: 16px;
}

.insights-right { display: flex; }
.pie-card { width: 100%; display: flex; justify-content: center; padding: 20px; }
.pie-card canvas { max-width: 100%; height: auto; }

.insight-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 22px 24px;
  box-shadow: 0 12px 30px rgba(27, 44, 72, 0.08);
  min-height: 180px;
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




