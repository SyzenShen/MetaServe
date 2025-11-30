import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token') || null,
    isLoading: false,
    error: null,
    organizations: []
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    currentUser: (state) => state.user,
    myOrganizations: (state) => state.organizations
  },

  actions: {
    async login(credentials) {
      this.isLoading = true
      this.error = null
      
      try {
        const response = await axios.post('/api/auth/login/', credentials)
        const { token, user } = response.data
        
        this.token = token
        this.user = user
        localStorage.setItem('token', token)
        
        // 设置axios默认header
        axios.defaults.headers.common['Authorization'] = `Token ${token}`
        
        return { success: true }
      } catch (error) {
        // 优先展示后端明确的错误信息
        const data = error.response?.data
        const msgFromSerializer = Array.isArray(data?.non_field_errors) ? data.non_field_errors[0]
          : (typeof data === 'string' ? data : null)
        const fallback = data?.message || data?.detail
        this.error = msgFromSerializer || fallback || '账号或密码错误'
        return { success: false, error: this.error }
      } finally {
        this.isLoading = false
      }
    },

    async register(userData) {
      this.isLoading = true
      this.error = null
      
      try {
        const response = await axios.post('/api/auth/register/', userData)
        return { success: true, message: '注册成功，请登录' }
      } catch (error) {
        const data = error.response?.data
        // serializer 校验错误兼容：可能是对象或列表
        let specificError = null
        if (typeof data === 'object' && data) {
          const fieldOrder = ['username', 'email', 'password', 'confirm_password', 'non_field_errors']
          for (const field of fieldOrder) {
            if (Array.isArray(data[field]) && data[field].length) {
              specificError = data[field][0]
              break
            }
          }
        }
        const fallback = data?.message || data?.detail
        this.error = specificError || fallback || '注册失败'
        return { success: false, error: this.error }
      } finally {
        this.isLoading = false
      }
    },

    async logout() {
      try {
        await axios.post('/api/auth/logout/')
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        this.token = null
        this.user = null
        localStorage.removeItem('token')
        delete axios.defaults.headers.common['Authorization']
      }
    },

    async fetchUser() {
      if (!this.token) return
      
      try {
        const response = await axios.get('/api/auth/profile/')
        this.user = response.data
      } catch (error) {
        console.error('Fetch user error:', error)
        // 不强制登出，保留 token，并继续携带认证头，避免影响后续接口调用
        // 如果确实是 401，可提示用户重新登录，但不移除 header
        if (error?.response?.status === 401) {
          this.error = '登录状态已过期，请重新登录'
        }
      }
    },

    async fetchOrganizations() {
      if (!this.token) {
        this.organizations = []
        return
      }
      try {
        const res = await axios.get('/api/auth/orgs/')
        const orgs = res.data?.organizations || []
        this.organizations = orgs
        // 供部分组件快速判断权限（例如 Navbar），避免重复请求
        window.__myOrganizations = orgs
      } catch (error) {
        console.warn('Fetch organizations error:', error?.response?.status, error?.message)
        this.organizations = []
        window.__myOrganizations = []
      }
    },

    initializeAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Token ${this.token}`
        // 并行拉取用户信息与组织信息，提升首屏权限判定的及时性
        this.fetchUser()
        this.fetchOrganizations()
        // 也同步放一个当前用户的全局快捷引用，部分纯脚本场景使用
        // 注意：仅在登录状态下设置，登出时会清理
        setTimeout(() => { window.__currentUser = this.user }, 0)
      }
    }
  }
})