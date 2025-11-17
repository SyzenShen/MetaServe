<template>
  <div class="workspace">
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="workspace-meta">
          <h1 class="workspace-title">Workspace</h1>
          <div class="workspace-breadcrumb" ref="breadcrumbRef">
            <span v-if="showBreadcrumbEllipsis" class="breadcrumb-ellipsis">…</span>
            <button v-if="currentFolderId !== null" class="breadcrumb-back" @click="navigateUp">
              Go Back
            </button>
            <button class="breadcrumb-item" :class="{ active: currentFolderId === null }" @click="navigateToRoot">
              All Files
            </button>
            <template v-for="(folder, index) in breadcrumbPath" :key="folder.id">
              <span class="breadcrumb-separator">/</span>
              <button
                class="breadcrumb-item"
                :class="{ active: index === breadcrumbPath.length - 1 }"
                @click="navigateToFolder(folder.id)"
              >
                {{ folder.name }}
              </button>
            </template>
          </div>
        </div>
        <div class="toolbar-actions-left">
          <button class="toolbar-btn primary" @click="showUploadDialogHandler">Upload</button>
          <button class="toolbar-btn primary" @click="showNewFolderDialogHandler">New Folder</button>
        </div>
      </div>
      <div class="toolbar-actions">
        <button class="toolbar-refresh" @click="refreshFiles" :disabled="isLoading">Refresh</button>
        <div class="view-switch">
          <button :class="{ active: viewMode === 'list' }" @click="setViewMode('list')">List</button>
          <button :class="{ active: viewMode === 'grid' }" @click="setViewMode('grid')">Grid</button>
        </div>
      </div>
    </header>

    <div class="workspace-body">
      <aside class="workspace-panel">
        <div class="panel-title">Directory</div>
        <div class="panel-content">
          <FolderTree />
        </div>
      </aside>

      <section class="workspace-canvas">
        <div class="canvas-surface">
          <div v-if="isLoading" class="canvas-overlay">
            <div class="overlay-card">
              <div class="spinner" />
              <p>Loading files…</p>
            </div>
          </div>
          <div v-else-if="error" class="canvas-overlay">
            <div class="overlay-card error">
              <h3>Load Failed</h3>
              <p>{{ error }}</p>
              <div class="overlay-actions">
                <button @click="refreshFiles">Retry</button>
                <button class="outline" @click="goHome">Go Home</button>
              </div>
            </div>
          </div>
          <div v-else class="canvas-content">
            <FileDisplay />
          </div>
        </div>
      </section>

      
    </div>

    <EnhancedUploadDialog v-if="showUploadDialog" @close="closeUploadDialog" />

    <div v-if="showNewFolderDialog" class="workspace-modal-overlay" @click="closeNewFolderDialog">
      <div class="workspace-modal" @click.stop>
        <NewFolderDialog @close="closeNewFolderDialog" />
      </div>
    </div>

    <div v-if="showNcbiDialog" class="workspace-modal-overlay" @click="closeNcbiDialog">
      <div class="workspace-modal" @click.stop>
        <div class="ncbi-modal">
          <h3>NCBI Data Download</h3>
          <p class="ncbi-tip">
            Enter an NCBI link (Gene, Protein, SRA, PubMed, etc.) and the system will auto-detect and download.
          </p>
          <input
            v-model="ncbiUrl"
            type="text"
            class="ncbi-input"
            placeholder="https://www.ncbi.nlm.nih.gov/..."
            :disabled="ncbiIsSubmitting"
          />
          <p v-if="ncbiError" class="ncbi-error">{{ ncbiError }}</p>
          <div class="ncbi-actions">
            <button class="toolbar-btn ghost" @click="closeNcbiDialog" :disabled="ncbiIsSubmitting">Cancel</button>
            <button class="toolbar-btn primary" @click="submitNcbiDownload" :disabled="ncbiIsSubmitting || !ncbiUrl.trim()">
              {{ ncbiIsSubmitting ? 'Downloading…' : 'Start Download' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <Transition name="workspace-toast">
      <div v-if="successMessage" class="workspace-toast">
        <div class="toast-content">
          <strong>Success</strong>
          <span>{{ successMessage }}</span>
        </div>
        <button class="toast-close" @click="successMessage = ''">×</button>
      </div>
    </Transition>
  </div>
</template>

<script>
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useFilesStore } from '../stores/files'
import axios from 'axios'
import FolderTree from '../components/FolderTree.vue'
import FileDisplay from '../components/FileDisplay.vue'
import EnhancedUploadDialog from '../components/EnhancedUploadDialog.vue'
import NewFolderDialog from '../components/NewFolderDialog.vue'

export default {
  name: 'FileList',
  components: {
    FolderTree,
    FileDisplay,
    EnhancedUploadDialog,
    NewFolderDialog
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const filesStore = useFilesStore()

    const successMessage = ref('')
    const showNcbiDialog = ref(false)
    const ncbiUrl = ref('')
    const ncbiIsSubmitting = ref(false)
    const ncbiError = ref('')

    const isLoading = computed(() => filesStore.isLoading)
    const error = computed(() => filesStore.error)
    const showUploadDialog = computed(() => filesStore.showUploadDialog)
    const showNewFolderDialog = computed(() => filesStore.showNewFolderDialog)

    const currentFolderId = computed(() => filesStore.currentFolderId)
    const breadcrumbPath = computed(() => filesStore.breadcrumb || [])
    const viewMode = computed(() => filesStore.viewMode)

    // 面包屑溢出检测，控制左侧省略号显示
    const breadcrumbRef = ref(null)
    const showBreadcrumbEllipsis = ref(false)
    const measureBreadcrumb = () => {
      const el = breadcrumbRef.value
      if (el) {
        // 如果面包屑总宽度超过容器宽度，则显示左侧省略号
        const overflow = el.scrollWidth > el.clientWidth + 2
        showBreadcrumbEllipsis.value = overflow
        // 自动滚到末尾，优先显示当前目录，左侧被隐去
        if (overflow) {
          el.scrollLeft = el.scrollWidth
        } else {
          el.scrollLeft = 0
        }
      }
    }

    const currentFiles = computed(() => filesStore.currentFiles || [])
    const currentFolders = computed(() => filesStore.currentFolders || [])
    const currentFilesCount = computed(() => currentFiles.value.length)
    const currentFoldersCount = computed(() => currentFolders.value.length)
    const totalSize = computed(() => currentFiles.value.reduce((sum, file) => sum + (file.file_size || 0), 0))

    const formatBytes = (bytes) => {
      if (!bytes) return '0 B'
      const units = ['B', 'KB', 'MB', 'GB', 'TB']
      const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
      const value = bytes / Math.pow(1024, exponent)
      return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`
    }
    const formattedTotalSize = computed(() => formatBytes(totalSize.value))

    const navigateToRoot = () => {
      filesStore.navigateToFolder(null)
    }

    const navigateToFolder = (folderId) => {
      filesStore.navigateToFolder(folderId)
    }

    const navigateUp = () => {
      filesStore.navigateUp()
    }

    const setViewMode = (mode) => {
      filesStore.setViewMode(mode)
    }

    const showUploadDialogHandler = () => {
      filesStore.toggleUploadDialog()
    }

    const showNewFolderDialogHandler = () => {
      filesStore.toggleNewFolderDialog()
    }

    const closeUploadDialog = () => {
      filesStore.closeAllDialogs()
    }

    const closeNewFolderDialog = () => {
      filesStore.closeAllDialogs()
    }

    const refreshFiles = async () => {
      await filesStore.fetchFiles(currentFolderId.value)
    }

    const openSearch = () => {
      router.push('/search')
    }

    const goHome = () => {
      router.push('/')
    }

    const openNcbiDialog = () => {
      ncbiUrl.value = ''
      ncbiError.value = ''
      showNcbiDialog.value = true
    }

    const closeNcbiDialog = () => {
      if (ncbiIsSubmitting.value) return
      showNcbiDialog.value = false
      ncbiUrl.value = ''
      ncbiError.value = ''
    }

    const submitNcbiDownload = async () => {
      if (!ncbiUrl.value.trim()) {
        ncbiError.value = 'Please enter a valid NCBI link'
        return
      }
      ncbiIsSubmitting.value = true
      ncbiError.value = ''
      try {
        const payload = { url: ncbiUrl.value.trim() }
        if (currentFolderId.value !== null && currentFolderId.value !== undefined) {
          payload.parent_folder = currentFolderId.value
        }
        const response = await axios.post('/api/files/ncbi/import/', payload)
      const fileTitle = response?.data?.file?.title || response?.data?.file?.file_name || 'File'
      successMessage.value = `Downloaded ${fileTitle} from NCBI`
        showNcbiDialog.value = false
        ncbiUrl.value = ''
        ncbiError.value = ''
        await filesStore.fetchFiles(currentFolderId.value)
      } catch (error) {
        console.error('NCBI download error:', error)
      ncbiError.value = error?.response?.data?.message || 'Download failed, please try again later'
      } finally {
        ncbiIsSubmitting.value = false
      }
    }

    const applyWorkspaceLayout = () => {
      nextTick(() => {
        const main = document.querySelector('main.container')
        if (main) {
          main.classList.add('workspace-main')
        }
      })
    }

    const resetWorkspaceLayout = () => {
      const main = document.querySelector('main.container')
      if (main) {
        main.classList.remove('workspace-main')
      }
    }

    onMounted(async () => {
      applyWorkspaceLayout()
      await filesStore.fetchFiles()
      nextTick(measureBreadcrumb)
      window.addEventListener('resize', measureBreadcrumb)
      // If entered via /files?ncbi=1, automatically open the NCBI download dialog
      const ncbiFlag = route.query?.ncbi
      if (ncbiFlag === '1' || ncbiFlag === 1 || ncbiFlag === true) {
        openNcbiDialog()
      // Optional: remove the query to avoid repeated popup on refresh
        const { ncbi, ...rest } = route.query
        router.replace({ path: route.path, query: { ...rest } })
      }
    })

    onBeforeUnmount(() => {
      resetWorkspaceLayout()
       window.removeEventListener('resize', measureBreadcrumb)
    })

    return {
      isLoading,
      error,
      showUploadDialog,
      showNewFolderDialog,
      successMessage,
      currentFolderId,
      breadcrumbPath,
      viewMode,
      currentFilesCount,
      currentFoldersCount,
      formattedTotalSize,
      navigateToRoot,
      navigateToFolder,
      navigateUp,
      setViewMode,
      showUploadDialogHandler,
      showNewFolderDialogHandler,
      closeUploadDialog,
      closeNewFolderDialog,
      refreshFiles,
      openSearch,
      goHome,
      showNcbiDialog,
      ncbiUrl,
      ncbiIsSubmitting,
      ncbiError,
      openNcbiDialog,
      closeNcbiDialog,
      submitNcbiDownload
    }
  }
}
</script>

<style scoped>
:global(main.container.workspace-main) {
  display: block;
  padding: 0 !important;
  margin: 0 !important;
  min-height: calc(100vh - 72px);
  width: 100%;
  max-width: none;
  background: transparent !important;
}

.workspace {
  min-height: calc(100vh - 72px);
  display: flex;
  flex-direction: column;
  background: #ffffff;
  width: 100%;
  overflow: hidden;
  --primary: rgb(58, 126, 185);
  --primary-hover: rgb(45, 102, 150);
  --primary-muted: rgba(58, 126, 185, 0.12);
}

.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 32px;
  padding: 20px 32px 18px;
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(27, 44, 72, 0.06);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex: 1; /* 左侧区域占据可用空间，防止被右侧挤压 */
}

.workspace-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  flex: 1; /* 允许面包屑区域伸缩，避免挤压按钮 */
}

.workspace-title {
  font-size: 22px;
  font-weight: 650;
  margin: 0;
  color: var(--text-primary);
}

.workspace-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap; /* 禁止换行，避免工具栏高度变化 */
  min-width: 0; /* 使其在父容器中可压缩 */
  flex: 1; /* 占据可用空间 */
  overflow-x: auto; /* 允许横向滚动以隐藏前缀 */
  overflow-y: hidden;
  justify-content: flex-start; /* 左对齐，修复 All Files 过右 */
  position: relative; /* 让省略号可绝对定位在左侧 */
  max-width: 60vw; /* 限制最大宽度，避免挤压按钮 */
}

.breadcrumb-item,
.breadcrumb-separator,
.breadcrumb-back {
  flex-shrink: 0; /* 防止子项被压缩变形，改为裁剪前面的 */
}

.breadcrumb-ellipsis {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  padding-left: 4px;
}

/* 隐藏面包屑滚动条，但仍可编程滚动 */
.workspace-breadcrumb::-webkit-scrollbar {
  width: 0;
  height: 0;
}
.workspace-breadcrumb { scrollbar-width: none; }

.breadcrumb-back {
  border: none;
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  font-size: 13px;
  padding: 4px 0;
}

.breadcrumb-item {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: background 0.2s ease, color 0.2s ease;
}

.breadcrumb-item.active {
  color: var(--text-primary);
  font-weight: 600;
}

.breadcrumb-item:hover {
  background: rgba(141, 141, 141, 0.12);
  color: var(--text-primary);
}

.breadcrumb-separator {
  color: var(--text-muted);
  font-size: 12px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-actions-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex: 0 0 auto; /* 固定按钮宽度，不随面包屑伸缩而移动 */
  margin-left: auto; /* 锚定到左侧区域最右端，避免与面包屑相互挤压导致位移 */
}

.view-switch {
  display: inline-flex;
  border: 1px solid rgba(27, 44, 72, 0.12);
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: transparent; /* 由按钮本身控制背景 */
}

.view-switch button {
  border: none;
  background: transparent;
  padding: 6px 12px; /* 缩小按钮尺寸 */
  font-size: 12px; /* 字体略小 */
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.2s ease, color 0.2s ease;
}

.view-switch button:hover {
  background: #dfe3e8; /* 未选中悬停稍深灰 */
}

/* 切换样式：未选中略深灰，选中为白色 */
.view-switch button + button {
  border-left: 1px solid rgba(27, 44, 72, 0.08);
}
.view-switch button {
  background: #e5e7eb; /* 未选中略深灰 */
  color: var(--text-secondary);
}
.view-switch button.active {
  background: #ffffff; /* 选中白色 */
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px var(--primary);
}

/* 右侧 Refresh 与 List/Grid 尺寸保持一致 */
.toolbar-refresh {
  border: 1px solid rgba(27, 44, 72, 0.12);
  background: #ffffff;
  color: var(--text-secondary);
  padding: 6px 12px; /* 与 .view-switch 一致尺寸 */
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px; /* 与切换按钮一致 */
  transition: all 0.2s ease;
}
.toolbar-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.toolbar-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(27, 44, 72, 0.12);
}

.toolbar-btn {
  border: 1px solid rgba(27, 44, 72, 0.12);
  background: #ffffff;
  color: var(--text-secondary);
  padding: 10px 22px; /* 略微增大按钮尺寸 */
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px; /* 字体稍大一点 */
  transition: all 0.2s ease;
}

.toolbar-btn.primary {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.toolbar-btn.ghost {
  background: transparent;
  color: var(--text-secondary);
}

.toolbar-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toolbar-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(27, 44, 72, 0.12);
}

.workspace-body {
  flex: 1;
  display: flex;
  align-items: stretch;
  overflow: hidden;
  background: #ffffff;
  width: 100%;
  min-height: calc(100vh - 72px);
}

.workspace-panel {
  width: 272px;
  background: #ffffff;
  border-right: 1px solid rgba(27, 44, 72, 0.08);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: calc(100vh - 72px);
}

.panel-title {
  padding: 18px 24px 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 16px;
  min-height: 0;
  background: #ffffff;
}

.workspace-canvas {
  flex: 1;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.canvas-surface {
  flex: 1;
  background: #ffffff;
  border-radius: 0; /* 去掉圆角，避免四周灰边视觉 */
  box-shadow: none; /* 去掉阴影，避免四周灰边视觉 */
  position: relative;
  overflow: hidden;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.canvas-content {
  flex: 1;
  display: flex;
  min-height: 0;
}

.canvas-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: center;
  align-items: center;
  zIndex: 2;
}

.overlay-card {
  background: #fff;
  border-radius: 16px;
  padding: 28px 36px;
  box-shadow: 0 18px 40px rgba(141, 141, 141, 0.12);
  text-align: center;
  color: var(--text-secondary);
}

.overlay-card.error {
  border: 1px solid rgba(244, 63, 94, 0.3);
}

.overlay-card h3 {
  margin-top: 0;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.overlay-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 18px;
}

.overlay-actions button {
  border: 1px solid var(--primary);
  background: var(--primary);
  color: #fff;
  border-radius: var(--radius-lg);
  padding: 8px 20px;
  cursor: pointer;
}

.overlay-actions button.outline {
  background: transparent;
  color: var(--primary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(141, 141, 141, 0.2);
  border-top-color: var(--primary);
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.9s linear infinite;
}

/* 右侧统计栏样式已移除 */

.workspace-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.workspace-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 45px rgba(0, 0, 0, 0.25);
  max-width: 520px;
  width: 100%;
  overflow: hidden;
}

.ncbi-modal {
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ncbi-modal h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.ncbi-tip {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.ncbi-input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(27, 44, 72, 0.18);
  border-radius: var(--radius-md);
  font-size: 14px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.ncbi-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(58, 126, 185, 0.15);
  outline: none;
}

.ncbi-error {
  margin: 0;
  font-size: 13px;
  color: #dc2626;
}

.ncbi-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.workspace-toast {
  position: fixed;
  right: 28px;
  bottom: 32px;
  background: #111827;
  color: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: 0 18px 40px rgba(15, 31, 68, 0.22);
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 20;
}

.toast-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toast-close {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: 20px;
  cursor: pointer;
}

.workspace-toast-enter-active,
.workspace-toast-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.workspace-toast-enter-from,
.workspace-toast-leave-to {
  transform: translateY(20px);
  opacity: 0;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

:deep(.waves-file-display) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

:deep(.waves-table-content) {
  flex: 1;
  overflow: auto;
}

@media (max-width: 1280px) {
  .workspace-insights {
    display: none;
  }
}

@media (max-width: 960px) {
  .workspace-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  /* 移动端取消左侧对齐边距 */
  .toolbar-actions-left {
    margin-left: 0;
  }

  .workspace-body {
    flex-direction: column;
  }

  .workspace-panel {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid rgba(27, 44, 72, 0.08);
  }

  .workspace-canvas {
    padding: 16px;
  }
}
</style>
