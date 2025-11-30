<template>
  <div id="app" class="app-full-center">
    <Navbar v-if="showNavbar" />
    <main class="container" :class="mainClass">
      <transition name="fade" mode="out-in">
        <router-view />
      </transition>
    </main>
    <LoadingOverlay />
    <!-- 全局 NCBI 下载弹窗 -->
    <GlobalNcbiDialog />
  </div>
</template>

<script>
import Navbar from './components/Navbar.vue'
import LoadingOverlay from './components/LoadingOverlay.vue'
import GlobalNcbiDialog from './components/GlobalNcbiDialog.vue'
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import { useRoute } from 'vue-router'

export default {
  name: 'App',
  components: {
    Navbar,
    LoadingOverlay,
    GlobalNcbiDialog
  },
  setup() {
    const authStore = useAuthStore()
    const route = useRoute()
    // 未登录首页('/')隐藏导航栏，其余页面或已登录显示
    const showNavbar = computed(() => authStore.isAuthenticated || route.path !== '/')
    // 未登录首页裁掉页面顶部20px
    const mainClass = computed(() => (!authStore.isAuthenticated && route.path === '/') ? 'home-top-crop' : '')
    return { showNavbar, mainClass }
  }
}
</script>
<style>
/* 全局路由渐隐/渐显过渡 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 250ms ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>