<template>
  <nav class="navbar navbar-default waves-transparent" role="navigation">
    <div class="container-fluid">
      <div class="navbar-header">
        <router-link to="/" class="navbar-brand">
          <img :src="logoSrc" alt="WAVES Logo" id="navbar-logo" @error="handleLogoError" />
          <span class="brand-text">MetaServe</span>
        </router-link>
      </div>
      
      <div class="navbar-collapse collapse in">
        <ul class="nav navbar-nav navbar-right">
          <!-- 主要导航项（移除 Home 链接） -->
          
          <template v-if="isAuthenticated">
            <li :class="{ active: $route.path === '/' }">
              <router-link to="/">Home</router-link>
            </li>
            <li :class="{ active: $route.path === '/files' }">
              <router-link to="/files">Files</router-link>
            </li>
            <li :class="{ active: $route.path === '/download' }">
              <router-link to="/download">Download</router-link>
            </li>
            <li :class="{ active: $route.path === '/search' }">
              <router-link to="/search">Search Files</router-link>
            </li>
            <!-- 细胞可视化入口，使用 SPA 路由，优先跳转最近发布的文件 -->
            <li :class="{ active: $route.path === '/cellxgene-app' }">
              <router-link :to="cellxgeneRoute">Cell Visualization</router-link>
            </li>
            <!-- 组织管理入口：仅超级用户显示，移动到 Cell Visualization 右侧 -->
            <li v-if="isSuperuser">
              <a href="/api/auth/orgs/ui/">management</a>
            </li>
            <li :class="{ active: $route.path === '/profile' }">
              <router-link to="/profile">Profile</router-link>
            </li>
          </template>

          
          <!-- 用户相关项（未登录时移除 Login 链接） -->
          <template v-if="!isAuthenticated">
            <!-- Login link removed -->
          </template>
          
          <template v-if="isAuthenticated">
            <li>
              <a href="#" @click.prevent="handleLogout">Logout</a>
            </li>
          </template>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useFilesStore } from '../stores/files'
import assetLogo from '../assets/images/logo.png'

export default {
  name: 'Navbar',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()
    
    const filesStore = useFilesStore()
    const isAuthenticated = computed(() => authStore.isAuthenticated)
    const currentUser = computed(() => authStore.currentUser)
    const isSuperuser = computed(() => !!authStore.currentUser?.is_superuser)
    const cellxgeneRoute = computed(() => {
      const lastFile = filesStore.lastPublishedCellxgeneFile
      return lastFile
        ? { path: '/cellxgene-app', query: { file: lastFile } }
        : { path: '/cellxgene-app' }
    })
    
    const handleLogout = async () => {
      await authStore.logout()
      router.push('/')
    }

    // Use dedicated /download page instead of global NCBI dialog
    const logoSrc = ref('/api/auth/logo.png')
    const handleLogoError = () => { logoSrc.value = assetLogo }
    
    return {
      isAuthenticated,
      currentUser,
      isSuperuser,
      cellxgeneRoute,
      handleLogout,
      logoSrc,
      handleLogoError
    }
  }
}
</script>

<style scoped>
.navbar.waves-transparent {
  background: var(--waves-navbar-transparent-bg);
  border: none;
  box-shadow: 0 1px 0 rgba(27, 44, 72, 0.08), 0 6px 12px rgba(0, 0, 0, 0.12);
  transition: all 0.3s ease;
  min-height: 72px; /* 与全局布局保持一致高度 */
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.navbar .container-fluid {
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  color: var(--waves-corporate-text) !important;
  font-weight: 700;
  text-decoration: none;
  height: 72px;
}

.navbar-brand:hover {
  color: var(--waves-corporate-text-light) !important;
  text-decoration: none;
}

#navbar-logo {
  height: 32px;
  width: auto;
  margin-right: 5px;
  margin-top: -2px;
}

.navbar-brand .brand-text {
  font-size: 18px;
  font-weight: 700;
  color: #4a4a4a !important;
  text-shadow: none !important;
}

.navbar-nav > li > a {
  display: flex;
  align-items: center;
  height: 72px;
  padding: 0 14px !important;
  font-size: 14px;
}


.navbar-nav > li > a:hover,
.navbar-nav > li > a:focus {
  color: rgb(58, 126, 185) !important;
  background-color: rgba(58, 126, 185, 0.08) !important;
  text-decoration: none;
}

.navbar-nav > li.active > a,
.navbar-nav > li.active > a:hover,
.navbar-nav > li.active > a:focus {
  color: rgb(58, 126, 185) !important;
  background-color: rgba(58, 126, 185, 0.14) !important;
  border-radius: 0;
}

.navbar-text {
  color: var(--waves-corporate-text-light) !important;
  font-weight: 500;
  margin: 15px 15px !important;
}



@media (max-width: 767px) {
  .navbar-collapse {
    background: var(--waves-navbar-transparent-bg);
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    margin-top: 10px;
    padding-top: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
  
  .brand-text {
    font-size: 16px;
  }
  
  #navbar-logo {
    height: 28px;
  }
  
  .navbar-nav > li > a {
    padding: 12px 15px !important;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  }
  
  .navbar-nav > li:last-child > a {
    border-bottom: none;
  }
  
  .navbar-text {
    padding: 12px 15px !important;
    margin: 0 !important;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  }
}

@media (min-width: 768px) and (max-width: 991px) {
  .brand-text {
    font-size: 17px;
  }
  
  #navbar-logo {
    height: 30px;
  }
  
  .navbar-nav > li > a {
    padding: 15px 12px;
  }
}
</style>
