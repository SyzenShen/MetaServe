<template>
  <div class="workspace">
    <!-- Workspace-style toolbar -->
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="workspace-meta">
          <h1 class="workspace-title">File Search</h1>
          <p class="search-subtitle">Use keywords and filters to quickly find files</p>
        </div>
      </div>
  <div class="toolbar-actions">
    <button class="toolbar-btn ghost" @click="clearFilters">Clear Filters</button>
  </div>
</header>

    <!-- Search Box -->
    <div class="search-box-container">
      <div class="search-box">
        <input
          v-model="searchQuery"
          @keyup.enter="performSearch"
          @input="onSearchInput"
          type="text"
          placeholder="Search files..."
          class="search-input"
        />
        <button @click="performSearch" class="search-button">
          <span v-if="!isSearching">Search</span>
          <span v-else>Searching...</span>
        </button>
      </div>
      
      <!-- Search Suggestions -->
      <div v-if="suggestions.length > 0" class="search-suggestions">
        <div
          v-for="suggestion in suggestions"
          :key="suggestion.value"
          @click="applySuggestion(suggestion)"
          class="suggestion-item"
        >
          <span class="suggestion-type">{{ translateLabel(suggestion.type) }}</span>
          <span class="suggestion-label">{{ translateLabel(suggestion.label) }}</span>
        </div>
      </div>
    </div>

    <div class="workspace-body">
      <!-- Filters Panel -->
      <aside class="workspace-panel">
        <div class="panel-title">Filters</div>
        <div class="panel-content">
        
        <!-- Document Type -->
        <div class="facet-group">
          <h4>Document Type</h4>
          <div class="facet-options">
            <label v-for="item in facets.document_type" :key="item.document_type" class="facet-option">
              <input
                type="checkbox"
                :value="item.document_type"
                v-model="selectedFilters.document_type"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.document_type) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        <!-- File Format -->
        <div class="facet-group">
          <h4>File Format</h4>
          <div class="facet-options">
            <label v-for="item in facets.file_format" :key="item.file_format" class="facet-option">
              <input
                type="checkbox"
                :value="item.file_format"
                v-model="selectedFilters.file_format"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.file_format) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        <!-- Organism -->
        <div class="facet-group" v-if="facets.organism && facets.organism.length > 0">
          <h4>Organism</h4>
          <div class="facet-options">
            <label v-for="item in facets.organism" :key="item.organism" class="facet-option">
              <input
                type="checkbox"
                :value="item.organism"
                v-model="selectedFilters.organism"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.organism) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        <!-- Project -->
        <div class="facet-group">
          <h4>Project</h4>
          <div class="facet-options">
            <label v-for="item in facets.project" :key="item.project" class="facet-option">
              <input
                type="checkbox"
                :value="item.project"
                v-model="selectedFilters.project"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.project) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        <!-- Experiment Type -->
        <div class="facet-group" v-if="facets.experiment_type && facets.experiment_type.length > 0">
          <h4>Experiment Type</h4>
          <div class="facet-options">
            <label v-for="item in facets.experiment_type" :key="item.experiment_type" class="facet-option">
              <input
                type="checkbox"
                :value="item.experiment_type"
                v-model="selectedFilters.experiment_type"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.experiment_type) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        <!-- Access Level -->
        <div class="facet-group">
          <h4>Access Level</h4>
          <div class="facet-options">
            <label v-for="item in facets.access_level" :key="item.access_level" class="facet-option">
              <input
                type="checkbox"
                :value="item.access_level"
                v-model="selectedFilters.access_level"
                @change="applyFilters"
              />
              <span>{{ translateLabel(item.access_level) }} ({{ item.count }})</span>
            </label>
          </div>
        </div>

        </div>
      </aside>

      <!-- Search Results Canvas -->
      <section class="workspace-canvas">
        <div class="canvas-surface">
        <div class="canvas-center">
        <!-- Search Info -->
        <div class="search-info" v-if="searchPerformed">
          <div class="results-summary">
            <span v-if="searchResults.pagination">
              Found {{ searchResults.pagination.total_count }} files
              (Page {{ searchResults.pagination.page }} of {{ searchResults.pagination.total_pages }})
            </span>
            <span v-else>Searching...</span>
          </div>
          
          <!-- Sort Options -->
          <div class="sort-options">
            <label>Sort:</label>
            <select v-model="sortBy" @change="applyFilters">
              <option value="uploaded_at">Upload Time</option>
              <option value="title">Title</option>
              <option value="file_size">File Size</option>
              <option value="project">Project</option>
            </select>
            <select v-model="sortOrder" @change="applyFilters">
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </select>
          </div>
        </div>

        <!-- Loading Overlay -->
        <div v-if="isSearching" class="canvas-overlay">
          <div class="overlay-card">
            <div class="spinner" />
            <p>Searching...</p>
          </div>
        </div>

        <!-- Results List -->
        <div v-else-if="searchResults.results && searchResults.results.length > 0" class="results-list canvas-content">
          <div
            v-for="file in searchResults.results"
            :key="file.id"
            class="result-item"
            @click="showFilePreview(file)"
          >
            <div class="file-icon">
              {{ getFileIcon(file.file_format) }}
            </div>
            
            <div class="file-info">
              <h3 class="file-title">{{ file.title || file.original_filename }}</h3>
              <p class="file-meta">
                <span class="project">{{ translateLabel(file.project) }}</span>
                <span class="format">{{ translateLabel(file.file_format) }}</span>
                <span class="size">{{ formatFileSize(file.file_size) }}</span>
                <span class="date">{{ formatDate(file.uploaded_at) }}</span>
              </p>
              <p v-if="file.organism" class="organism">{{ translateLabel(file.organism) }}</p>
              <p v-if="file.description" class="description">{{ file.description }}</p>
              <div v-if="file.tags_list && file.tags_list.length > 0" class="tags">
                <span v-for="tag in file.tags_list" :key="tag" class="tag">{{ tag }}</span>
              </div>
            </div>
            
            <div class="waves-action-group">
              <button 
                @click.stop="downloadFile(file)" 
                class="waves-action-btn waves-download-btn"
                title="Download File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 20H19V18H5M19 9H15V3H9V9H5L12 16L19 9Z" fill="currentColor"/>
                </svg>
              </button>
              <button 
                @click.stop="showFilePreview(file)" 
                class="waves-action-btn waves-view-btn"
                title="Preview File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 5C7 5 2.73 8.11 1 12C2.73 15.89 7 19 12 19C17 19 21.27 15.89 23 12C21.27 8.11 17 5 12 5ZM12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17ZM12 9C10.34 9 9 10.34 9 12C9 13.66 10.34 15 12 15C13.66 15 15 13.66 15 12C15 10.34 13.66 9 12 9Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- No Results State -->
        <div v-else-if="searchPerformed && !isSearching" class="no-results canvas-content">
          <div class="no-results-icon"></div>
          <h3>No matching files found</h3>
          <p>Try adjusting search keywords or filter options</p>
          <div class="search-tips">
            <h4>Search Tips:</h4>
            <ul>
              <li>Use <code>project:ProjectName</code> to search by project</li>
              <li>Use <code>organism:Species</code> to search by organism</li>
              <li>Use <code>format:FASTQ</code> to search by format</li>
              <li>Combine terms: <code>human RNA-seq project:MyLab</code></li>
            </ul>
          </div>
        </div>

        <!-- Initial State -->
        <div v-else class="initial-state canvas-content">
          <div class="welcome-icon"></div>
          <h3>Start searching your files</h3>
          <p>Enter keywords above, or use the filters on the left</p>
        </div>

        <!-- Pagination -->
        <div v-if="searchResults.pagination && searchResults.pagination.total_pages > 1" class="pagination canvas-content">
          <button
            @click="goToPage(searchResults.pagination.page - 1)"
            :disabled="!searchResults.pagination.has_previous"
            class="page-btn"
          >
            Previous
          </button>
          
          <span class="page-info">
            Page {{ searchResults.pagination.page }} / {{ searchResults.pagination.total_pages }}
          </span>
          
          <button
            @click="goToPage(searchResults.pagination.page + 1)"
            :disabled="!searchResults.pagination.has_next"
            class="page-btn"
          >
            Next
          </button>
        </div>
        </div> <!-- /.canvas-center -->
        </div>
      </section>
      
    </div>

    <!-- 文件预览模态框 -->
    <FilePreviewModal
      v-if="showPreviewModal"
      :file="selectedFile"
      @close="closePreview"
    />
  </div>
</template>

<script>
import { ref, reactive, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore } from '../stores/files'
import FilePreviewModal from '../components/FilePreviewModal.vue'

export default {
  name: 'FileSearch',
  components: {
    FilePreviewModal
  },
  setup() {
    const router = useRouter()
    const filesStore = useFilesStore()
    
    // 响应式数据
    const searchQuery = ref('')
    const isSearching = ref(false)
    const searchPerformed = ref(false)
    const suggestions = ref([])
    const searchResults = reactive({
      results: [],
      pagination: null,
      facets: {},
      query_info: {}
    })
    
    // 筛选器状态
    const facets = reactive({
      document_type: [],
      file_format: [],
      organism: [],
      project: [],
      experiment_type: [],
      access_level: []
    })
    
    const selectedFilters = reactive({
      document_type: [],
      file_format: [],
      organism: [],
      project: [],
      experiment_type: [],
      access_level: []
    })
    
    // 排序选项
    const sortBy = ref('uploaded_at')
    const sortOrder = ref('desc')

    // Insights
    const totalCount = computed(() => {
      return (searchResults.pagination && searchResults.pagination.total_count) || (searchResults.results?.length || 0)
    })
    const facetsCount = computed(() => Object.keys(facets).length)
    const selectedCount = computed(() => Object.values(selectedFilters).reduce((sum, arr) => sum + arr.length, 0))
    
    // 预览相关
    const showPreviewModal = ref(false)
    const selectedFile = ref(null)
    
    // 分页
    const currentPage = ref(1)
    
    // 搜索建议防抖
    let suggestionTimeout = null
    
    // 方法
    const performSearch = async () => {
      if (isSearching.value) return
      
      isSearching.value = true
      searchPerformed.value = true
      
      try {
        const params = {
          q: searchQuery.value,
          page: currentPage.value,
          sort_by: sortBy.value,
          sort_order: sortOrder.value,
          ...getFilterParams()
        }
        
        const response = await filesStore.searchFiles(params)
        
        Object.assign(searchResults, response)
        Object.assign(facets, response.facets || {})
        
      } catch (error) {
        console.error('Search failed:', error)
        // 可以添加错误提示
      } finally {
        isSearching.value = false
      }
    }
    
    const onSearchInput = () => {
      // 清除之前的定时器
      if (suggestionTimeout) {
        clearTimeout(suggestionTimeout)
      }
      
      // 设置新的定时器
      suggestionTimeout = setTimeout(async () => {
        if (searchQuery.value.length >= 2) {
          try {
            const response = await filesStore.getSearchSuggestions(searchQuery.value)
            suggestions.value = response.suggestions || []
          } catch (error) {
        console.error('Failed to fetch search suggestions:', error)
          }
        } else {
          suggestions.value = []
        }
      }, 300)
    }
    
    const applySuggestion = (suggestion) => {
      searchQuery.value = suggestion.value
      suggestions.value = []
      performSearch()
    }
    
    const applyFilters = () => {
      currentPage.value = 1
      performSearch()
    }
    
    const clearFilters = () => {
      Object.keys(selectedFilters).forEach(key => {
        selectedFilters[key] = []
      })
      applyFilters()
    }
    
    const getFilterParams = () => {
      const params = {}
      Object.keys(selectedFilters).forEach(key => {
        if (selectedFilters[key].length > 0) {
          params[key] = selectedFilters[key].join(',')
        }
      })
      return params
    }
    
    const goToPage = (page) => {
      currentPage.value = page
      performSearch()
    }
    
    const showFilePreview = (file) => {
      selectedFile.value = file
      showPreviewModal.value = true
    }
    
    const closePreview = () => {
      showPreviewModal.value = false
      selectedFile.value = null
    }
    
    const downloadFile = async (file) => {
      try {
        await filesStore.downloadFile(file.id, file.original_filename)
      } catch (error) {
        console.error('Download failed:', error)
      }
    }
    
    const getFileIcon = (format) => {
      return ''
    }
    
    const formatFileSize = (bytes) => {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    // Map common Chinese labels to English for display
    const translateLabel = (value) => {
      if (value === null || value === undefined) return ''
      const str = String(value)
      const map = {
        '默认项目': 'Default Project',
        '公开': 'Public',
        '内部': 'Internal',
        '限制': 'Restricted',
        '人类': 'Human',
        '小鼠': 'Mouse',
        '斑马鱼': 'Zebrafish',
        '图片': 'Images',
        '视频': 'Videos',
        '文档': 'Documents'
      }
      return map[str] || str
    }
    
    // 初始化加载筛选器数据
    const loadFacets = async () => {
      try {
        const response = await filesStore.getFacets()
        Object.assign(facets, response.facets || {})
      } catch (error) {
        console.error('Failed to load filter data:', error)
      }
    }
    
    // 将页面主体(main.container)切换为工作区全宽布局，消除左右留白
    const applyWorkspaceLayout = () => {
      // 等待主容器渲染后再添加类
      const main = document.querySelector('main.container')
      if (main) {
        main.classList.add('workspace-main')
      }
    }

    const resetWorkspaceLayout = () => {
      const main = document.querySelector('main.container')
      if (main) {
        main.classList.remove('workspace-main')
      }
    }

    // 生命周期
    onMounted(() => {
      applyWorkspaceLayout()
      // 加载可选项
      loadFacets()
      // 进入页面默认在 Dataset：预选文档类型并触发一次搜索
      if (selectedFilters.document_type.length === 0) {
        selectedFilters.document_type = ['Dataset']
        applyFilters()
      }
    })

    onBeforeUnmount(() => {
      resetWorkspaceLayout()
    })
    
    return {
      searchQuery,
      isSearching,
      searchPerformed,
      suggestions,
      searchResults,
      facets,
      selectedFilters,
      sortBy,
      sortOrder,
      showPreviewModal,
      selectedFile,
      currentPage,
      performSearch,
      onSearchInput,
      applySuggestion,
      applyFilters,
      clearFilters,
      goToPage,
      showFilePreview,
      closePreview,
      downloadFile,
      getFileIcon,
      formatFileSize,
      formatDate,
      translateLabel,
      totalCount,
      facetsCount,
      selectedCount
    }
  }
}
</script>

<style scoped>
/* 覆盖 App.vue 中 main.container 的居中与留白，使工作区充满视口宽度 */
:global(main.workspace-main) {
  display: block;
  padding: 0;
  margin: 0;
  min-height: calc(100vh - 72px);
  width: 100%;
  max-width: none;
}
/* Workspace-style header (aligned to FileList.vue) */
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
  border-bottom: none; /* 去除搜索框上方的分割线 */
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.workspace-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.workspace-title {
  font-size: 22px;
  font-weight: 650;
  margin: 0;
  color: var(--text-primary);
}

.search-subtitle {
  color: var(--text-secondary);
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-btn {
  border: 1px solid rgba(27, 44, 72, 0.12);
  background: #fff;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.toolbar-btn.primary {
  background: rgb(58, 126, 185);
  color: #fff;
  border-color: rgb(58, 126, 185);
}
.toolbar-btn.primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.toolbar-btn.ghost:hover {
  background: rgba(141, 141, 141, 0.12);
  color: rgb(58, 126, 185);
}
.file-search-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
  background: var(--waves-surface-primary);
  min-height: 100vh;
}

.search-header {
  text-align: center;
  margin-bottom: 2rem;
}

.search-header h1 {
  font-size: 2.5rem;
  color: var(--waves-text-primary);
  margin-bottom: 0.75rem;
  font-weight: 600;
}

.search-subtitle {
  color: var(--waves-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.search-box-container {
  position: relative;
  margin-bottom: 2rem;
}

.search-box {
  display: flex;
  max-width: 980px;
  margin: 0 auto;
  box-shadow: var(--waves-shadow-lg);
  border-radius: var(--waves-radius-xl);
  overflow: hidden;
  border: 1px solid var(--waves-border-light);
  background: var(--waves-surface-secondary);
}

.search-input {
  flex: 1;
  padding: 1rem 1.5rem;
  border: none;
  font-size: 1.125rem;
  outline: none;
  background: transparent;
  color: var(--waves-text-primary);
}

.search-input::placeholder {
  color: var(--waves-text-secondary);
}

.search-button {
  padding: 1rem 2rem;
  background: rgb(58, 126, 185);
  color: white;
  border: none;
  font-size: 1.125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.search-button:hover {
  background: rgb(45, 102, 150);
  transform: translateY(-1px);
}

.search-suggestions {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 980px;
  background: var(--waves-surface-secondary);
  border: 1px solid var(--waves-border-light);
  border-top: none;
  border-radius: 0 0 var(--waves-radius-xl) var(--waves-radius-xl);
  box-shadow: var(--waves-shadow-lg);
  z-index: 1000;
  backdrop-filter: blur(8px);
}

.suggestion-item {
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  border-bottom: 1px solid var(--waves-border-light);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  transition: all 0.3s ease;
}

.suggestion-item:hover {
  background: var(--waves-primary-50);
  color: var(--waves-primary-700);
}

.suggestion-item:last-child {
  border-bottom: none;
}

.suggestion-type {
  background: var(--waves-primary-100);
  color: var(--waves-primary-700);
  padding: 0.25rem 0.75rem;
  border-radius: var(--waves-radius-full);
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.search-content {
  /* replaced by .workspace-body */
  display: contents;
}

/* old sidebar styles replaced by .workspace-panel */

.facets-sidebar h3 {
  margin-top: 0;
  color: var(--waves-text-primary);
  border-bottom: 2px solid var(--waves-primary-500);
  padding-bottom: 0.75rem;
  font-weight: 600;
  font-size: 1.125rem;
}

.facet-group {
  margin-bottom: 1.75rem;
}

.facet-group h4 {
  margin-bottom: 0.75rem;
  color: var(--waves-text-primary);
  font-size: 1rem;
  font-weight: 500;
}

.facet-options {
  max-height: 200px;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.facet-options::-webkit-scrollbar {
  width: 6px;
}

.facet-options::-webkit-scrollbar-track {
  background: var(--waves-surface-primary);
  border-radius: var(--waves-radius-full);
}

.facet-options::-webkit-scrollbar-thumb {
  background: var(--waves-border-medium);
  border-radius: var(--waves-radius-full);
}

.facet-options::-webkit-scrollbar-thumb:hover {
  background: var(--waves-border-dark);
}

.facet-option {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0.25rem 0;
  transition: color 0.3s ease;
}

.facet-option:hover {
  color: var(--waves-primary-600);
}

.facet-option input {
  margin-right: 0.75rem;
  accent-color: rgb(58, 126, 185);
}

.clear-filters-btn {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--waves-danger-500);
  color: white;
  border: none;
  border-radius: var(--waves-radius-lg);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.clear-filters-btn:hover {
  background: var(--waves-danger-600);
  transform: translateY(-1px);
  box-shadow: var(--waves-shadow-md);
}

.search-results {
  min-height: 400px;
}

.search-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: #fff;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(27, 44, 72, 0.06);
}

.sort-options {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sort-options label {
  color: var(--waves-text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.sort-options select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--waves-border-light);
  border-radius: var(--waves-radius-lg);
  background: var(--waves-surface-primary);
  color: var(--waves-text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.sort-options select:focus {
  outline: none;
  border-color: var(--waves-primary-500);
  box-shadow: 0 0 0 3px var(--waves-primary-100);
}

/* loading now handled by .canvas-overlay + .overlay-card */

.results-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--waves-surface-secondary);
  border: 1px solid var(--waves-border-light);
  border-radius: var(--waves-radius-xl);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--waves-shadow-sm);
  width: 100%;
}

.result-item:hover {
  box-shadow: var(--waves-shadow-lg);
  transform: translateY(-2px);
  border-color: var(--waves-primary-200);
}

.file-icon {
  font-size: 2.5rem;
  flex-shrink: 0;
  color: var(--waves-primary-500);
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-title {
  margin: 0 0 0.75rem 0;
  color: var(--waves-text-primary);
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.4;
}

.file-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 0.5rem;
  color: var(--waves-text-secondary);
  font-size: 0.875rem;
}

.file-meta > span {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.organism, .description {
  margin: 0.375rem 0;
  color: var(--waves-text-primary);
  font-size: 0.875rem;
  line-height: 1.5;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.tag {
  background: var(--waves-primary-100);
  color: var(--waves-primary-700);
  padding: 0.25rem 0.75rem;
  border-radius: var(--waves-radius-full);
  font-size: 0.75rem;
  font-weight: 500;
}

/* 与文件管理界面的操作按钮一致的风格 */
.waves-action-group {
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.result-item:hover .waves-action-group {
  opacity: 1;
}

.waves-action-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--waves-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--waves-surface-secondary);
  color: var(--waves-text-secondary);
}

.waves-action-btn svg {
  width: 16px;
  height: 16px;
}

.waves-download-btn:hover {
  background: #10b981;
  color: white;
  transform: scale(1.1);
}

.waves-view-btn:hover {
  background: #2563eb;
  color: white;
  transform: scale(1.1);
}

.no-results, .initial-state {
  text-align: center;
  padding: 4rem 1.5rem;
  color: var(--waves-text-secondary);
  background: var(--waves-surface-secondary);
  border-radius: var(--waves-radius-xl);
  border: 1px solid var(--waves-border-light);
  margin: 2rem 0;
}

.no-results-icon, .welcome-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
  color: var(--waves-primary-400);
}

.search-tips {
  margin-top: 2rem;
  text-align: left;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
  background: var(--waves-surface-primary);
  padding: 1.5rem;
  border-radius: var(--waves-radius-lg);
  border: 1px solid var(--waves-border-light);
}

.search-tips h4 {
  color: var(--waves-text-primary);
  margin-bottom: 1rem;
  font-weight: 600;
}

.search-tips ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.search-tips li {
  margin-bottom: 0.75rem;
  padding-left: 2rem;
  position: relative;
  line-height: 1.5;
}

.search-tips li:before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
}

.search-tips code {
  background: var(--waves-primary-50);
  color: var(--waves-primary-700);
  padding: 0.25rem 0.5rem;
  border-radius: var(--waves-radius-sm);
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  font-size: 0.875em;
  font-weight: 500;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  margin-top: 2rem;
  padding: 1.5rem;
  background: var(--waves-surface-secondary);
  border-radius: var(--waves-radius-xl);
  border: 1px solid var(--waves-border-light);
}

.page-btn {
  padding: 0.75rem 1.5rem;
  background: var(--waves-primary-500);
  color: white;
  border: none;
  border-radius: var(--waves-radius-lg);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-btn:hover:not(:disabled) {
  background: var(--waves-primary-600);
  transform: translateY(-1px);
  box-shadow: var(--waves-shadow-md);
}

.page-btn:disabled {
  background: var(--waves-gray-400);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.page-info {
  color: var(--waves-text-secondary);
  font-weight: 500;
  font-size: 0.875rem;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .search-content {
    grid-template-columns: 280px 1fr;
    gap: 1.5rem;
  }
  
  .facets-sidebar {
    padding: 1rem;
  }
}

@media (max-width: 768px) {
  .file-search-container {
    padding: 1rem;
  }
  
  .search-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .facets-sidebar {
    position: static;
    order: 2;
  }
  
  .search-results {
    order: 1;
  }
  
  .search-info {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .result-item {
    flex-direction: column;
    gap: 1rem;
  }
  
  .file-actions {
    flex-direction: row;
    justify-content: center;
    gap: 0.75rem;
  }
  
  .action-btn {
    min-width: auto;
    flex: 1;
  }
  
  .pagination {
    flex-direction: column;
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .search-header h1 {
    font-size: 2rem;
  }
  
  .search-box {
    flex-direction: column;
  }
  
  .search-button {
    border-radius: 0 0 var(--waves-radius-xl) var(--waves-radius-xl);
  }
  
  .file-actions {
    flex-direction: column;
  }
}
</style>
<style scoped>
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
  border-radius: 20px;
  box-shadow: 0 20px 48px rgba(15, 31, 68, 0.08);
  position: relative;
  overflow: hidden;
  padding: 24px 0;
}

.canvas-center {
  /* 改为靠左布局并占满可用宽度 */
  max-width: none;
  width: 100%;
  margin: 0;
  padding: 0 24px; /* 保持左右内边距，与画布一致 */
}

.canvas-content {
  background: transparent;
  border: none;
  border-radius: 0;
  padding: 0;
}

.canvas-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(17, 24, 39, 0.06);
  backdrop-filter: blur(2px);
}

.overlay-card {
  background: #fff;
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 12px 30px rgba(27, 44, 72, 0.08);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(27, 44, 72, 0.12);
  border-top-color: var(--primary, rgb(58, 126, 185));
  border-radius: 50%;
  margin: 0 auto 10px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.workspace-insights {
  width: 260px;
  background: rgba(255, 255, 255, 0.9);
  border-left: 1px solid rgba(27, 44, 72, 0.08);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.insight-card {
  background: #fff;
  border: 1px solid rgba(27, 44, 72, 0.08);
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 12px 30px rgba(27, 44, 72, 0.08);
}

.insight-card.highlight {
  border-color: var(--primary, rgb(58, 126, 185));
}

.insight-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary, rgb(58, 126, 185));
}

.insight-label {
  font-size: 13px;
  color: var(--text-muted);
}

.insight-caption {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 1280px) {
  .workspace-insights { display: none; }
}

@media (max-width: 960px) {
  .workspace-toolbar { flex-direction: column; align-items: flex-start; gap: 16px; }
  .toolbar-actions { width: 100%; justify-content: flex-start; flex-wrap: wrap; }
  .workspace-body { flex-direction: column; }
  .workspace-panel { width: 100%; border-right: none; border-bottom: 1px solid rgba(27, 44, 72, 0.08); }
  .workspace-canvas { padding: 16px; }
}
</style>
