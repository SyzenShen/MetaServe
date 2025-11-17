import { defineStore } from 'pinia'
import axios from 'axios'

export const useNcbiStore = defineStore('ncbi', {
  state: () => ({
    showDialog: false,
    url: '',
    isSubmitting: false,
    error: ''
  }),
  actions: {
    open() {
      this.error = ''
      this.url = ''
      this.showDialog = true
    },
    close() {
      if (this.isSubmitting) return
      this.showDialog = false
      this.url = ''
      this.error = ''
    },
    async submit() {
      const trimmed = (this.url || '').trim()
      if (!trimmed) {
        this.error = 'Please enter a valid NCBI link'
        return
      }
      this.isSubmitting = true
      this.error = ''
      try {
        const payload = { url: trimmed }
        const response = await axios.post('/api/files/ncbi/import/', payload)
        // 简单成功处理：关闭弹窗
        this.showDialog = false
        this.url = ''
        this.error = ''
        // 可选：在此触发全局提示或刷新文件列表（如需要）
      } catch (error) {
        console.error('NCBI download error:', error)
        this.error = error?.response?.data?.message || 'Download failed, please try again later'
      } finally {
        this.isSubmitting = false
      }
    }
  }
})