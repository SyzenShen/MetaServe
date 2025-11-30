<template>
  <div class="waves-file-display">
    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'" class="waves-list-view">
      <!-- 表格头部 -->
      <div class="waves-table-header">
        <div class="waves-header-cell waves-name-cell">
          <svg class="waves-header-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 2H6C4.9 2 4.01 2.9 4.01 4L4 20C4 21.1 4.89 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM18 20H6V4H13V9H18V20Z" fill="currentColor"/>
          </svg>
          Name
        </div>
        <div class="waves-header-cell waves-size-cell">
          <svg class="waves-header-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z" fill="currentColor"/>
          </svg>
          Size
        </div>
        <div class="waves-header-cell waves-date-cell">
          <svg class="waves-header-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 3H18V1H16V3H8V1H6V3H5C3.89 3 3.01 3.9 3.01 5L3 19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM19 19H5V8H19V19ZM7 10H12V15H7V10Z" fill="currentColor"/>
          </svg>
          Modified
        </div>
        <div class="waves-header-cell waves-action-cell">
          <svg class="waves-header-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 8C13.1 8 14 7.1 14 6C14 4.9 13.1 4 12 4C10.9 4 10 4.9 10 6C10 7.1 10.9 8 12 8ZM12 10C10.9 10 10 10.9 10 12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12C14 10.9 13.1 10 12 10ZM12 16C10.9 16 10 16.9 10 18C10 19.1 10.9 20 12 20C13.1 20 14 19.1 14 18C14 16.9 13.1 16 12 16Z" fill="currentColor"/>
          </svg>
          Actions
        </div>
      </div>
      
      <!-- 表格内容 -->
      <div class="waves-table-content">
        <!-- 文件夹 -->
        <div 
          v-for="folder in folders"
          :key="`folder-${folder.id}`"
          class="waves-table-row waves-folder-row"
          @click="navigateToFolder(folder.id)"
        >
          <div class="waves-cell waves-name-cell">
            <div class="waves-file-icon waves-folder-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 4H4C2.89 4 2.01 4.89 2.01 6L2 18C2 19.11 2.89 20 4 20H20C21.11 20 22 19.11 22 18V8C22 6.89 21.11 6 20 6H12L10 4Z" fill="currentColor"/>
              </svg>
            </div>
          <div class="waves-file-info">
              <div class="waves-file-name">{{ folder.name }}</div>
              <div class="waves-file-type">Folder<template v-if="getOrganizationNameForFolder(folder)"> · {{ getOrganizationNameForFolder(folder) }}</template></div>
            </div>
          </div>
          <div class="waves-cell waves-size-cell">
            <span class="waves-size-text">{{ formatFileSize(folder.folder_size) }}</span>
          </div>
          <div class="waves-cell waves-date-cell">
            <span class="waves-date-text">{{ formatDate(folder.created_at) }}</span>
          </div>
        <div class="waves-cell waves-action-cell">
          <div class="waves-action-group">
            <button 
              class="waves-action-btn waves-download-btn"
              @click.stop="downloadFolder(folder.id)"
              title="Download Folder"
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 20H19V18H5M19 9H15V3H9V9H5L12 16L19 9Z" fill="currentColor"/>
              </svg>
            </button>
            <button
              class="waves-action-btn waves-share-btn"
              @click.stop="copyShareLinkForFolder(folder)"
              title="Share Link"
            >
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                <circle cx="6" cy="12" r="2.5" fill="currentColor"/>
                <circle cx="18" cy="6" r="2.5" fill="currentColor"/>
                <circle cx="18" cy="18" r="2.5" fill="currentColor"/>
                <path d="M7.9 11.2 L15.5 7.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M7.9 12.8 L15.5 16.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
            <button
              v-if="folder.parent == null ? (folder.can_manage_permissions || (folder.is_owner && !folder.organization && !folder.is_public)) : (folder.is_owner && !folder.organization && !folder.is_public)"
              class="waves-action-btn"
              @click.stop="openPermissionDialog({ type: 'folder', id: folder.id, name: folder.name, organization_name: getOrganizationNameForFolder(folder) })"
              title="权限设置"
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 1a2 2 0 012 2v1.07a7.002 7.002 0 013.183 1.318l.758-.757a2 2 0 112.828 2.828l-.757.758A7.002 7.002 0 0119.93 11H21a2 2 0 012 2s0 0 0 0a2 2 0 01-2 2h-1.07a7.002 7.002 0 01-1.318 3.183l.757.758a2 2 0 11-2.828 2.828l-.758-.757A7.002 7.002 0 0114 19.93V21a2 2 0 11-4 0v-1.07a7.002 7.002 0 01-3.183-1.318l-.758.757a2 2 0 11-2.828-2.828l.757-.758A7.002 7.002 0 014.07 14H3a2 2 0 110-4h1.07a7.002 7.002 0 011.318-3.183l-.757-.758a2 2 0 112.828-2.828l.758.757A7.002 7.002 0 0110 4.07V3a2 2 0 012-2zm0 6a5 5 0 100 10A5 5 0 0012 7z" fill="currentColor"/>
              </svg>
            </button>
            <button 
              class="waves-action-btn waves-delete-btn"
              @click.stop="deleteFolder(folder.id)"
              title="Delete Folder"
            >
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 4H15.5L14.5 3H9.5L8.5 4H5V6H19M6 19C6 20.1 6.9 21 8 21H16C17.1 21 18 20.1 18 19V7H6V19Z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
        </div>
        
        <!-- 文件 -->
        <div 
          v-for="file in files"
          :key="`file-${file.id}`"
          class="waves-table-row waves-file-row"
          @click="showFilePreview(file)"
        >
          <div class="waves-cell waves-name-cell">
            <div class="waves-file-icon waves-document-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4.01 2.9 4.01 4L4 20C4 21.1 4.89 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM18 20H6V4H13V9H18V20Z" fill="currentColor"/>
              </svg>
            </div>
            <div class="waves-file-info">
              <div class="waves-file-name">{{ file.original_filename }}</div>
              <div class="waves-file-type">{{ getFileType(file.original_filename) }}<template v-if="getOrganizationNameForFile(file)"> · {{ getOrganizationNameForFile(file) }}</template></div>
              <!-- 下载进度条（仅在有进度时显示） -->
              <div v-if="downloadProgress[file.id] !== undefined" class="waves-download-progress">
                <div class="waves-progress-track">
                  <div class="waves-progress-fill" :style="{ width: (downloadProgress[file.id] || 0) + '%' }"></div>
                </div>
                <span class="waves-progress-text">{{ (downloadProgress[file.id] || 0) }}%</span>
              </div>
            </div>
          </div>
          <div class="waves-cell waves-size-cell">
            <span class="waves-size-text">{{ formatFileSize(file.file_size) }}</span>
          </div>
          <div class="waves-cell waves-date-cell">
            <span class="waves-date-text">{{ formatDate(file.uploaded_at) }}</span>
          </div>
          <div class="waves-cell waves-action-cell">
            <div class="waves-action-group">
              <!-- 先显示 Cellxgene（仅 .h5ad 有），否则用占位保持下载按钮纵向对齐 -->
              <template v-if="isH5ad(file.original_filename)">
                <button
                  class="waves-action-btn waves-cellxgene-btn"
                  @click.stop="sendToCellxgene(file)"
                  title="Send to Cellxgene"
                >
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <!-- 细胞膜：随按钮颜色变化的实心圆 -->
                    <circle cx="12" cy="12" r="8" fill="currentColor" />
                    <!-- 细胞核：白色实心圆，保持对比度 -->
                    <circle class="cell-nucleus" cx="12" cy="12" r="3" fill="#ffffff" />
                    <!-- 细胞器：白色点状 -->
                    <circle class="cell-organelle" cx="8.5" cy="9.5" r="1" fill="#ffffff" />
                    <circle class="cell-organelle" cx="15.5" cy="14.5" r="1.2" fill="#ffffff" />
                    <!-- 胞质纹理：白色曲线 -->
                    <path class="cell-texture" d="M7 12c2.5 1.5 4.8 1.5 6 0" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                </button>
              </template>

              <!-- 下载按钮固定在第二列，实现纵向对齐 -->
              <button 
                class="waves-action-btn waves-download-btn"
                @click="downloadFile(file)"
                title="Download File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 20H19V18H5M19 9H15V3H9V9H5L12 16L19 9Z" fill="currentColor"/>
                </svg>
              </button>
              <button
                class="waves-action-btn waves-share-btn"
                @click.stop="copyShareLinkForFile(file)"
                title="Share Link"
              >
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                  <circle cx="6" cy="12" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="6" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="18" r="2.5" fill="currentColor"/>
                  <path d="M7.9 11.2 L15.5 7.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <path d="M7.9 12.8 L15.5 16.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
              <button
                v-if="file.is_owner && !(currentFolder && (currentFolder.is_public || currentFolder.organization))"
                class="waves-action-btn"
                @click.stop="openPermissionDialog({ type: 'file', id: file.id, name: file.original_filename, organization_name: getOrganizationNameForFile(file) })"
                title="权限设置"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 1a2 2 0 012 2v1.07a7.002 7.002 0 013.183 1.318l.758-.757a2 2 0 112.828 2.828l-.757.758A7.002 7.002 0 0119.93 11H21a2 2 0 012 2s0 0 0 0a2 2 0 01-2 2h-1.07a7.002 7.002 0 01-1.318 3.183l.757.758a2 2 0 11-2.828 2.828l-.758-.757A7.002 7.002 0 0114 19.93V21a2 2 0 11-4 0v-1.07a7.002 7.002 0 01-3.183-1.318l-.758.757a2 2 0 11-2.828-2.828l.757-.758A7.002 7.002 0 014.07 14H3a2 2 0 110-4h1.07a7.002 7.002 0 011.318-3.183l-.757-.758a2 2 0 112.828-2.828l.758.757A7.002 7.002 0 0110 4.07V3a2 2 0 012-2zm0 6a5 5 0 100 10A5 5 0 0012 7z" fill="currentColor"/>
                </svg>
              </button>
              <!-- 下载控制：暂停/继续/取消 -->
              <template v-if="downloadActive[file.id] || downloadProgress[file.id] !== undefined">
                <button 
                  class="waves-action-btn"
                  @click.stop="pauseDownload(file.id)"
                  v-if="!downloadPaused[file.id]"
                  title="Pause Download"
                >
                  ||
                </button>
                <button 
                  class="waves-action-btn"
                  @click.stop="resumeDownload(file.id, file.original_filename || `file_${file.id}`, file.file_size)"
                  v-else
                  title="Resume Download"
                >
                  ▶
                </button>
                <button 
                  class="waves-action-btn waves-delete-btn"
                  @click.stop="cancelDownload(file.id)"
                  title="Cancel Download"
                >
                  ✕
                </button>
              </template>
              <button 
                class="waves-action-btn waves-delete-btn"
                v-if="file.can_delete"
                @click.stop="deleteFile(file.id)"
                title="Delete File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M19 4H15.5L14.5 3H9.5L8.5 4H5V6H19M6 19C6 20.1 6.9 21 8 21H16C17.1 21 18 20.1 18 19V7H6V19Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 网格视图 -->
    <div v-else class="waves-grid-view">
      <div class="waves-grid-content">
        <!-- 文件夹 -->
        <div 
          v-for="folder in folders"
          :key="`folder-${folder.id}`"
          class="waves-grid-item waves-folder-card"
          @click="navigateToFolder(folder.id)"
        >
          <div class="waves-card-header">
            <div class="waves-item-icon waves-folder-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 4H4C2.89 4 2.01 4.89 2.01 6L2 18C2 19.11 2.89 20 4 20H20C21.11 20 22 19.11 22 18V8C22 6.89 21.11 6 20 6H12L10 4Z" fill="currentColor"/>
              </svg>
            </div>
            <div class="waves-item-actions">
              <button 
                class="waves-action-btn waves-download-btn"
                @click.stop="downloadFolder(folder.id)"
                title="Download Folder"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 20H19V18H5M19 9H15V3H9V9H5L12 16L19 9Z" fill="currentColor"/>
                </svg>
              </button>
              <button
                class="waves-action-btn waves-share-btn"
                @click.stop="copyShareLinkForFolder(folder)"
                title="Share Link"
              >
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                  <circle cx="6" cy="12" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="6" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="18" r="2.5" fill="currentColor"/>
                  <path d="M7.9 11.2 L15.5 7.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <path d="M7.9 12.8 L15.5 16.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
              <button 
                class="waves-action-btn waves-delete-btn"
                @click.stop="deleteFolder(folder.id)"
                title="Delete Folder"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M19 4H15.5L14.5 3H9.5L8.5 4H5V6H19M6 19C6 20.1 6.9 21 8 21H16C17.1 21 18 20.1 18 19V7H6V19Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="waves-card-body">
            <div class="waves-item-name">{{ folder.name }}</div>
            <div class="waves-item-meta">
              <span class="waves-item-type">Folder<template v-if="getOrganizationNameForFolder(folder)"> · {{ getOrganizationNameForFolder(folder) }}</template></span>
              <span class="waves-item-size">{{ formatFileSize(folder.folder_size) }}</span>
              <span class="waves-item-date">{{ formatDate(folder.created_at) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 文件 -->
        <div 
          v-for="file in files"
          :key="`file-${file.id}`"
          class="waves-grid-item waves-file-card"
          @click="showFilePreview(file)"
        >
          <div class="waves-card-header">
            <div class="waves-item-icon waves-document-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4.01 2.9 4.01 4L4 20C4 21.1 4.89 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM18 20H6V4H13V9H18V20Z" fill="currentColor"/>
              </svg>
            </div>
            <div class="waves-item-actions">
              <template v-if="isH5ad(file.original_filename)">
                <button 
                  class="waves-action-btn waves-cellxgene-btn"
                  @click.stop="sendToCellxgene(file)"
                  title="Send to Cellxgene"
                >
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <!-- 细胞膜：随按钮颜色变化的实心圆 -->
                    <circle cx="12" cy="12" r="8" fill="currentColor" />
                    <!-- 细胞核：白色实心圆，保持对比度 -->
                    <circle class="cell-nucleus" cx="12" cy="12" r="3" fill="#ffffff" />
                    <!-- 细胞器：白色点状 -->
                    <circle class="cell-organelle" cx="8.5" cy="9.5" r="1" fill="#ffffff" />
                    <circle class="cell-organelle" cx="15.5" cy="14.5" r="1.2" fill="#ffffff" />
                    <!-- 胞质纹理：白色曲线 -->
                    <path class="cell-texture" d="M7 12c2.5 1.5 4.8 1.5 6 0" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                </button>
              </template>

              <!-- 下载按钮固定在第二列，实现纵向对齐 -->
              <button 
                class="waves-action-btn waves-download-btn"
                @click="downloadFile(file)"
                title="Download File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 20H19V18H5M19 9H15V3H9V9H5L12 16L19 9Z" fill="currentColor"/>
                </svg>
              </button>
              <button 
                class="waves-action-btn waves-share-btn"
                @click.stop="copyShareLinkForFile(file)"
                title="Share Link"
              >
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none">
                  <circle cx="6" cy="12" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="6" r="2.5" fill="currentColor"/>
                  <circle cx="18" cy="18" r="2.5" fill="currentColor"/>
                  <path d="M7.9 11.2 L15.5 7.8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                  <path d="M7.9 12.8 L15.5 16.2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
              <button 
                class="waves-action-btn waves-delete-btn"
                @click.stop="deleteFile(file.id)"
                title="Delete File"
              >
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M19 4H15.5L14.5 3H9.5L8.5 4H5V6H19M6 19C6 20.1 6.9 21 8 21H16C17.1 21 18 20.1 18 19V7H6V19Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="waves-card-body">
            <div class="waves-item-name" :title="file.original_filename">{{ file.original_filename }}</div>
            <div class="waves-item-meta">
              <span class="waves-item-type">{{ getFileType(file.original_filename) }}<template v-if="getOrganizationNameForFile(file)"> · {{ getOrganizationNameForFile(file) }}</template></span>
              <span class="waves-item-size">{{ formatFileSize(file.file_size) }}</span>
              <span class="waves-item-date">{{ formatDate(file.uploaded_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="isEmpty" class="waves-empty-state">
      <div class="waves-empty-icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M10 4H4C2.89 4 2.01 4.89 2.01 6L2 18C2 19.11 2.89 20 4 20H20C21.11 20 22 19.11 22 18V8C22 6.89 21.11 6 20 6H12L10 4Z" fill="currentColor"/>
        </svg>
      </div>
      <div class="waves-empty-content">
        <h3 class="waves-empty-title">This folder is empty</h3>
        <p class="waves-empty-description">Upload files or create a new folder to get started</p>
        <div class="waves-empty-actions">
          <button class="waves-btn waves-btn-primary">
            <svg class="waves-btn-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C4.9 2 4.01 2.9 4.01 4L4 20C4 21.1 4.89 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM18 20H6V4H13V9H18V20ZM8 15.01L8.01 15H16V17H8V15.01ZM16 11H8V13H16V11ZM12 7V9H16V7H12Z" fill="currentColor"/>
            </svg>
            Upload Files
          </button>
          <button class="waves-btn waves-btn-secondary">
            <svg class="waves-btn-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 4H4C2.89 4 2.01 4.89 2.01 6L2 18C2 19.11 2.89 20 4 20H20C21.11 20 22 19.11 22 18V8C22 6.89 21.11 6 20 6H12L10 4Z" fill="currentColor"/>
            </svg>
            New Folder
          </button>
        </div>
      </div>
    </div>

    <FilePreviewModal
      v-if="showPreviewModal"
      :file="selectedFile"
      @close="closePreview"
    />

    <!-- Permission Settings Dialog -->
    <div v-if="permissionState.visible" class="dialog-backdrop" @click="closePermissionDialog">
      <div class="dialog" @click.stop>
        <h3 class="dialog-title">Permission Settings</h3>
        <p class="dialog-desc">Target: {{ permissionState.targetName }}</p>
        <div class="form-group">
          <label>{{ permissionState.targetType==='folder' ? 'Managing Entity' : 'File Ownership' }}</label>
          <select v-model="permissionState.selectedScope" class="form-control">
            <option value="public">Public (accessible to any logged-in user)</option>
            <option value="personal">Personal</option>
            <option v-for="o in permissionState.orgs" :key="o.id" :value="`org:${o.id}`">
              Organization: {{ o.name }}
            </option>
          </select>
        </div>
        <p v-if="permissionState.error" class="status error">{{ permissionState.error }}</p>
        <div class="dialog-actions">
          <button class="btn" @click="submitPermission" :disabled="permissionState.submitting">Save</button>
          <button class="btn cancel" @click="closePermissionDialog" :disabled="permissionState.submitting">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useFilesStore } from '../stores/files'
import axios from 'axios'
import FilePreviewModal from './FilePreviewModal.vue'

const filesStore = useFilesStore()
const router = useRouter()

// Show "Send to Cellxgene" only for .h5ad files
const isH5ad = (name) => {
  const n = (name || '').toLowerCase()
  return n.endsWith('.h5ad')
}

// Computed
const viewMode = computed(() => filesStore.viewMode)
const folders = computed(() => filesStore.currentFolders)
const files = computed(() => filesStore.currentFiles)
const currentFolder = computed(() => filesStore.currentFolder)
const isEmpty = computed(() => folders.value.length === 0 && files.value.length === 0)
// Download states from Pinia store
const downloadProgress = computed(() => filesStore.downloadProgress)
const downloadPaused = computed(() => filesStore.downloadPaused)
const downloadActive = computed(() => filesStore.downloadActive)

// Methods
const navigateToFolder = (folderId) => {
  filesStore.navigateToFolder(folderId)
}

const showPreviewModal = ref(false)
const selectedFile = ref(null)
const showFilePreview = (file) => {
  selectedFile.value = file
  showPreviewModal.value = true
}
const closePreview = () => {
  showPreviewModal.value = false
  selectedFile.value = null
}

const deleteFolder = async (folderId) => {
  // Wrap confirm dialog in Promise to ensure true sync behavior
  const confirmed = await new Promise((resolve) => {
    // Use setTimeout to show dialog in next event loop tick
    setTimeout(() => {
      const result = confirm('Are you sure you want to delete this folder?')
      resolve(result)
    }, 0)
  })
  
  if (!confirmed) {
    return // User clicked cancel; do not proceed
  }
  
  const result = await filesStore.deleteFolder(folderId)
  if (!result.success) {
    alert(`Delete failed: ${result.error}`)
  }
}

const deleteFile = async (fileId) => {
  // Wrap confirm dialog in Promise to ensure true sync behavior
  const confirmed = await new Promise((resolve) => {
    // Use setTimeout to show dialog in next event loop tick
    setTimeout(() => {
      const result = confirm('Are you sure you want to delete this file?')
      resolve(result)
    }, 0)
  })
  
  if (!confirmed) {
    return // User clicked cancel; do not proceed
  }
  
  const result = await filesStore.deleteFile(fileId)
  if (!result.success) {
    alert(`Delete failed: ${result.error}`)
  }
}

const downloadFile = async (file, retryCount = 0) => {
  const maxRetries = 3
  const retryDelay = 1000 * (retryCount + 1) // 递增延迟

  try {
    // Get token
    const token = localStorage.getItem('token')
    if (!token) {
      filesStore.showErrorNotification('Please log in first')
      return
    }

    // Show download start notification
    if (retryCount === 0) {
      filesStore.showDownloadNotification(`Starting download: ${file.original_filename || file.name || `file_${file.id}`}`)
    }

    // For large files use breakpoint-resume download in store
    if (file.file_size && file.file_size > 50 * 1024 * 1024) { // 50MB以上
      const result = await filesStore.downloadFile(file.id, file.original_filename || `file_${file.id}`, file.file_size)
      if (!result.success) {
        throw new Error(result.error || 'Download failed')
      }
      return
    }

    // Use fetch with auth and add timeout control
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时

    const response = await fetch(`/api/files/${file.id}/download/`, {
      method: 'GET',
      headers: {
        'Authorization': `Token ${token}`
      },
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      // Check for auth issues
      if (response.status === 401) {
        filesStore.showErrorNotification('Session expired, please log in again')
        return
      }
      // Check for file not found
      if (response.status === 404) {
        filesStore.showErrorNotification('File not found or has been removed')
        return
      }
      throw new Error(`Download failed: ${response.status} ${response.statusText}`)
    }

    // Check response content type to avoid downloading error page
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('text/html') || contentType.includes('application/json')) {
      const errorText = await response.text()
      throw new Error(errorText || 'Server returned an error page')
    }

    // Get file blob
    const blob = await response.blob()
    
    // Check blob size to avoid empty files
    if (blob.size === 0) {
      throw new Error('Downloaded file is empty')
    }
    
    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.original_filename || `file_${file.id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // Revoke object URL
    window.URL.revokeObjectURL(url)
    
  } catch (error) {
    console.error(`Download failed (attempt ${retryCount + 1}/${maxRetries + 1}):`, error)
    
    // Check if network error and can retry
    const isNetworkError = error.name === 'AbortError' || 
                          error.message.includes('fetch') || 
                          error.message.includes('network') ||
                          error.message.includes('timeout')
    
    if (isNetworkError && retryCount < maxRetries) {
      console.log(`Retrying in ${retryDelay}ms...`)
      setTimeout(() => {
        downloadFile(file, retryCount + 1)
      }, retryDelay)
      return
    }
    
    // Show user-friendly error message
    let errorMessage = error.message
    if (error.name === 'AbortError') {
      errorMessage = 'Download timed out, please check your network'
    } else if (error.message.includes('fetch')) {
      errorMessage = 'Network connection failed, please check your network'
    }
    
    filesStore.showErrorNotification(`Download failed: ${errorMessage}`)
  }
}

// Permission dialog state and methods
const permissionState = reactive({
  visible: false,
  targetType: null, // 'file' | 'folder'
  targetId: null,
  targetName: '',
  currentOrg: null,
  accessLevel: 'Internal',
  orgs: [],
  selectedScope: 'personal',
  submitting: false,
  error: ''
})

const openPermissionDialog = (target) => {
  permissionState.visible = true
  permissionState.targetType = target.type
  permissionState.targetId = target.id
  permissionState.targetName = target.name
  permissionState.currentOrg = target.organization_name || null
  permissionState.error = ''
  // Default scope based on current folder organization
  permissionState.selectedScope = 'personal'
  if (permissionState.targetType === 'folder') {
    const cf = currentFolder.value
    if (cf?.is_public) permissionState.selectedScope = 'public'
    else if (cf?.organization) permissionState.selectedScope = `org:${cf.organization}`
    else permissionState.selectedScope = 'personal'
  } else {
    const cf = currentFolder.value
    if (cf?.is_public) permissionState.selectedScope = 'public'
    else if (cf?.organization) permissionState.selectedScope = `org:${cf.organization}`
    else permissionState.selectedScope = 'personal'
  }
  // Fetch organizations
  fetchMyOrganizations()
}

const closePermissionDialog = () => {
  if (permissionState.submitting) return
  permissionState.visible = false
}

async function fetchMyOrganizations(){
  try{
    const res = await axios.get('/api/auth/orgs/')
    const all = res.data?.organizations || []
    const meId = (window.__currentUser && window.__currentUser.id) || null
    permissionState.orgs = all.filter(o => (o.role === 'owner') || (meId && o.owner_id === meId))
  }catch(e){
    permissionState.orgs = []
  }
}

async function submitPermission(){
  if (permissionState.submitting) return
  permissionState.submitting = true
  permissionState.error = ''
  try{
    const scope = permissionState.selectedScope
    if (permissionState.targetType === 'folder'){
      // Public vs Personal/Organization
      let body = {}
      if (scope === 'public') {
        body = { is_public: true, organization: null }
      } else if (scope === 'personal') {
        body = { is_public: false, organization: null }
      } else if (scope.startsWith('org:')) {
        const orgId = scope.split(':')[1]
        body = { is_public: false, organization: Number(orgId) }
      }
      const url = `/api/files/folders/${permissionState.targetId}/`
      await axios.put(url, body)
      await filesStore.fetchFiles(filesStore.currentFolderId)
    } else {
      // Files: same logic as folders
      if (scope === 'public') {
        const url = `/api/files/${permissionState.targetId}/`
        await axios.put(url, { access_level: 'Public' })
      } else {
        // personal or org:xxx -> Internal; organization determined by parent folder
        const url = `/api/files/${permissionState.targetId}/`
        await axios.put(url, { access_level: 'Internal' })
      }
      await filesStore.fetchFiles(filesStore.currentFolderId)
    }
    permissionState.visible = false
  }catch(e){
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || 'Update failed'
    permissionState.error = msg
  }finally{
    permissionState.submitting = false
  }
}

// Download controls: pause/resume/cancel (delegated to store)
const pauseDownload = (fileId) => {
  try { filesStore.pauseDownload(fileId) } catch (_) {}
}
const resumeDownload = async (fileId, filename, fileSize) => {
  try { await filesStore.resumeDownload(fileId, filename, fileSize) } catch (_) {}
}
const cancelDownload = async (fileId) => {
  try { await filesStore.cancelDownload(fileId) } catch (_) {}
}

const copyText = async (text) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (_) {}
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.top = '-1000px'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch (_) {
    return false
  }
}

const copyShareLinkForFile = async (file) => {
  const origin = window.location.origin
  const link = `${origin}/download?file=${file.id}`
  const ok = await copyText(link)
  filesStore.showDownloadNotification(ok ? 'Share link copied' : 'Copy failed')
}

const copyShareLinkForFolder = async (folder) => {
  const origin = window.location.origin
  const link = `${origin}/download?folder=${folder.id}`
  const ok = await copyText(link)
  filesStore.showDownloadNotification(ok ? 'Share link copied' : 'Copy failed')
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const waitForCellxgeneReady = async (datasetFileName, timeout = 60000, interval = 2000) => {
  const baseUrl = import.meta.env.VITE_CELLXGENE_URL || '/cellxgene/'
  if (/^https?:\/\//.test(baseUrl)) {
    // External address (e.g., http://localhost:5005/); cannot poll across origins
    await sleep(4000)
    return true
  }
  const cleanBaseUrl = baseUrl.replace(/\/$/, '')
  const endpoint = `${cleanBaseUrl}/api/v0.2/config`
  const expected = (datasetFileName || '').replace(/\.[^.]+$/, '')
  const start = Date.now()

  while (Date.now() - start < timeout) {
    try {
      const res = await fetch(endpoint, { method: 'GET', cache: 'no-store' })
      if (res.ok) {
        const json = await res.json()
        const datasetName = json?.config?.displayNames?.dataset || ''
        if (!expected || datasetName === expected) {
          return true
        }
      }
    } catch (err) {
      console.warn('Failed to check Cellxgene status:', err)
    }
    await sleep(interval)
  }

  throw new Error('Cellxgene loading timed out, please try again later')
}

// Send to Cellxgene and navigate to preview page
const sendToCellxgene = async (file) => {
  console.log('Start sending to Cellxgene...', file)
  const name = file.original_filename || ''
  if (!name.toLowerCase().endsWith('.h5ad')) {
    filesStore.showErrorNotification('Only .h5ad files can be sent to Cellxgene')
    console.error('Unsupported file type:', name)
    return
  }

  console.log(`Calling publishToCellxgene, file ID: ${file.id}`)
  try {
    filesStore.showLoadingOverlay('Sending file to Cellxgene...')
    const result = await filesStore.publishToCellxgene(file.id)
    console.log('publishToCellxgene result:', result)

    if (result && result.success) {
      // Backend returns actual filename copied to Cellxgene data dir (with safe prefix)
      const publishedFile = result.data?.published_file
      const fallbackName = name.split('/').pop() || name
      const fileNameForPreview = publishedFile || fallbackName
      filesStore.setLastCellxgeneFile(fileNameForPreview)
      console.log(
          `Publish succeeded. Redirecting to /cellxgene-app with: ${fileNameForPreview}`,
        { publishedFile, fallbackName }
      )

      try {
    filesStore.showLoadingOverlay('Cellxgene is loading data, please wait...')
        await waitForCellxgeneReady(fileNameForPreview, 90000, 3000)
      } catch (waitError) {
    console.error('Waiting for Cellxgene data load failed:', waitError)
    filesStore.showErrorNotification(waitError.message || 'Cellxgene load timeout')
        return
      }
      // Navigate to wrapper page for preview, pass actual filename
      router.push({
        path: '/cellxgene-app',
        query: { file: fileNameForPreview }
      })
    } else {
    console.error('Publish failed, result from store:', result)
    filesStore.showErrorNotification(result?.error || 'Publish failed, see console logs')
    }
  } catch (error) {
    console.error('Exception during publishToCellxgene:', error)
    filesStore.showErrorNotification('Unknown error when sending to Cellxgene')
  } finally {
    filesStore.hideLoadingOverlay()
  }
}

const downloadFolder = async (folderId) => {
  try {
    // Get token
    const token = localStorage.getItem('token')
    if (!token) {
      alert('Please log in first')
      return
    }

    // Use fetch for authenticated folder download
    const response = await fetch(`/file_download/download/folder/${folderId}/`, {
      method: 'GET',
      headers: {
        'Authorization': `Token ${token}`,
        'Accept': 'application/zip'
      }
    })

    if (!response.ok) {
      if (response.status === 401) {
        alert('Session expired, please log in again')
        return
      }
      const text = await response.text().catch(() => '')
      throw new Error(`Download failed: ${response.status} ${response.statusText}${text ? ' - ' + text : ''}`)
    }

    // Get file blob
    const blob = await response.blob()
    
    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `folder_${folderId}.zip` // folder download usually ZIP
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    // Revoke object URL
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Folder download failed:', error)
    alert(`Download failed: ${error.message}`)
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US') + ' ' + date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const getFileType = (filename) => {
  if (!filename) return 'Unknown file'
  const ext = filename.split('.').pop()?.toLowerCase()
  
  const typeMap = {
    // Images
    'jpg': 'Image', 'jpeg': 'Image', 'png': 'Image', 'gif': 'Image', 'bmp': 'Image', 'svg': 'Image',
    // Documents
    'pdf': 'PDF Document', 'doc': 'Word Document', 'docx': 'Word Document', 'txt': 'Text File', 'rtf': 'Rich Text File',
    // Spreadsheets
    'xls': 'Excel Spreadsheet', 'xlsx': 'Excel Spreadsheet', 'csv': 'CSV File',
    // Presentations
    'ppt': 'PowerPoint', 'pptx': 'PowerPoint',
    // Archives
    'zip': 'Archive', 'rar': 'Archive', '7z': 'Archive', 'tar': 'Archive', 'gz': 'Archive',
    // Audio
    'mp3': 'Audio', 'wav': 'Audio', 'flac': 'Audio', 'aac': 'Audio',
    // Video
    'mp4': 'Video', 'avi': 'Video', 'mkv': 'Video', 'mov': 'Video', 'wmv': 'Video',
    // Code
    'js': 'JavaScript', 'html': 'HTML File', 'css': 'CSS File', 'py': 'Python File', 'java': 'Java File', 'cpp': 'C++ File'
  }
  
  return typeMap[ext] || 'Unknown File'
}

const getOrganizationNameForFile = (file) => {
  const cf = currentFolder.value
  if (cf && cf.organization_name) return cf.organization_name
  const pid = file?.parent_folder
  if (pid) {
    const f = folders.value.find(x => x.id === pid)
    return f?.organization_name || null
  }
  return null
}

const getOrganizationNameForFolder = (folder) => {
  if (folder?.is_public) return 'Public'
  return folder?.organization_name || null
}
</script>

<style scoped>
/* 企业级文件显示组件样式 */
.waves-file-display {
  height: 100%;
  background: var(--waves-surface-primary);
  overflow: hidden;
}

/* 列表视图样式 */
.waves-list-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.waves-table-header {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(135deg, var(--waves-primary-50), var(--waves-primary-100));
  border-bottom: 2px solid var(--waves-border-light);
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--waves-text-primary);
}

.waves-header-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.waves-header-icon {
  width: 16px;
  height: 16px;
  color: var(--waves-primary-600);
}

.waves-name-cell {
  flex: 1;
  min-width: 250px;
}

.waves-size-cell {
  width: 120px;
  justify-content: center;
}

.waves-date-cell {
  width: 180px;
  justify-content: center;
}

.waves-action-cell {
  width: 140px;
  justify-content: flex-start;
}

.waves-table-content {
  flex: 1;
  overflow-y: auto;
  background: var(--waves-surface-primary);
}

.waves-table-row {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f3f2f1;
  transition: all 0.2s ease;
  cursor: pointer;
}

.waves-table-row:hover {
  background: var(--waves-surface-secondary);
  transform: translateX(4px);
  border-left: 4px solid var(--waves-primary-500);
}

.waves-folder-row {
  background: linear-gradient(135deg, var(--waves-primary-25), transparent);
}

.waves-cell {
  display: flex;
  align-items: center;
}

.waves-cell.waves-name-cell {
  flex: 1;
  min-width: 250px;
  gap: 1rem;
}

.waves-cell.waves-size-cell,
.waves-cell.waves-date-cell {
  justify-content: center;
}
.waves-cell.waves-action-cell {
  justify-content: flex-start;
}

.waves-file-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--waves-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.waves-folder-icon {
  background: linear-gradient(135deg, var(--waves-primary-500), var(--waves-primary-600));
  color: white;
}

.waves-document-icon {
  background: linear-gradient(135deg, var(--waves-secondary-500), var(--waves-secondary-600));
  color: white;
}

/* 列表视图：文件夹图标改为浅灰、背景中性 */
.waves-list-view .waves-folder-icon {
  background: var(--waves-surface-secondary);
  color: var(--waves-text-secondary);
  border: 1px solid var(--waves-border-light);
}

/* 列表视图：文件图标同步为浅灰、背景中性 */
.waves-list-view .waves-document-icon {
  background: var(--waves-surface-secondary);
  color: var(--waves-text-secondary);
  border: 1px solid var(--waves-border-light);
}

.waves-list-view .waves-file-icon svg {
  color: inherit;
  fill: currentColor;
}

.waves-file-icon svg {
  width: 20px;
  height: 20px;
}

.waves-file-info {
  flex: 1;
  min-width: 0;
}

.waves-file-name {
  font-weight: 500;
  color: var(--waves-text-primary);
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.waves-file-type {
  font-size: 0.75rem;
  color: var(--waves-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.waves-size-text,
.waves-date-text {
  font-size: 0.875rem;
  color: var(--waves-text-secondary);
}

.waves-action-group {
  display: flex;
  gap: 0.25rem;
  margin-left: -12px;
  opacity: 1;
  transition: opacity 0.3s ease;
}

/* 保持与 hover 一致，避免仅在悬停时出现 */
.waves-table-row .waves-action-group {
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
  transition: all 0.2s ease;
  background: var(--waves-surface-secondary);
  color: var(--waves-text-secondary);
}

.waves-action-btn svg {
  width: 18px;
  height: 18px;
}
/* 让 Cellxgene 图标更大一些，仅影响该按钮 */
.waves-cellxgene-btn svg {
  width: 22px;
  height: 22px;
}

/* 用于占位，保证下载按钮纵向对齐 */
.waves-action-placeholder {
  width: 32px;
  height: 32px;
  display: inline-block;
}

.waves-action-btn:not(.waves-download-btn):not(.waves-delete-btn):not(.waves-cellxgene-btn):not(.waves-share-btn):hover {
  background: var(--primary, #2563eb);
  color: #fff;
  transform: scale(1.1);
}

.waves-share-btn {
  background: var(--waves-surface-secondary);
  color: var(--waves-text-secondary);
}
.waves-share-btn:hover {
  background: #5b21b6;
  color: #fff;
  transform: scale(1.1);
}

.waves-download-btn:hover {
  background: #10b981;
  color: #fff;
  transform: scale(1.1);
}

.waves-delete-btn:hover {
  background: #ef4444;
  color: #fff;
  transform: scale(1.1);
}

/* 发送到 Cellxgene 按钮样式 */
.waves-cellxgene-btn:hover {
  background: var(--primary, rgb(58, 126, 185));
  color: #fff;
  transform: scale(1.1);
}
/* 悬停时让细胞结构保持可见：膜反白，核/细胞器/纹理切换为主色 */
.waves-cellxgene-btn:hover .cell-nucleus,
.waves-cellxgene-btn:hover .cell-organelle {
  fill: var(--primary, rgb(58, 126, 185));
}
.waves-cellxgene-btn:hover .cell-texture {
  stroke: var(--primary, rgb(58, 126, 185));
}

/* 下载进度条 */
.waves-download-progress {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.waves-progress-track {
  flex: 1;
  height: 6px;
  background: var(--waves-surface-secondary);
  border-radius: 999px;
  overflow: hidden;
}
.waves-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  transition: width 0.2s ease;
}
.waves-progress-text {
  font-size: 12px;
  color: var(--waves-text-secondary);
}

/* 网格视图样式 */
.waves-grid-view {
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
  background: var(--waves-surface-primary);
}

.waves-grid-content {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}

.waves-grid-item {
  background: var(--waves-surface-secondary);
  border: 1px solid var(--waves-border-light);
  border-radius: var(--waves-radius-lg);
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
}

.waves-grid-item:hover {
  transform: translateY(-4px);
  box-shadow: var(--waves-shadow-lg);
  border-color: var(--waves-primary-300);
}

.waves-folder-card {
  background: linear-gradient(135deg, var(--waves-surface-secondary), var(--waves-surface-secondary)); /* 淡化色彩，突出浅灰图标 */
}

.waves-card-header {
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--waves-border-light);
}

.waves-grid-item .waves-item-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--waves-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  /* Grid 模式下的文件/文件夹图标使用浅灰 */
  color: var(--waves-text-secondary);
  opacity: 0.85;
}

.waves-grid-item .waves-item-icon svg {
  width: 24px;
  height: 24px;
  color: inherit; /* 继承浅灰色 */
  fill: currentColor; /* 使用当前颜色填充路径 */
}

.waves-item-actions {
  display: flex;
  gap: 0.25rem;
  margin-left: -12px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.waves-grid-item:hover .waves-item-actions {
  opacity: 1;
}

.waves-card-body {
  padding: 1rem;
}

.waves-item-name {
  font-weight: 500;
  color: var(--waves-text-primary);
  margin-bottom: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.waves-item-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.waves-item-type,
.waves-item-size,
.waves-item-date {
  font-size: 0.75rem;
  color: var(--waves-text-secondary);
}

.waves-item-type {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

/* 空状态样式 */
.waves-empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
}

.waves-empty-icon {
  width: 120px;
  height: 120px;
  background: var(--waves-surface-secondary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 2rem;
  color: var(--waves-text-secondary);
  opacity: 0.6;
}

.waves-empty-icon svg {
  width: 60px;
  height: 60px;
}

.waves-empty-content {
  max-width: 400px;
}

.waves-empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--waves-text-primary);
  margin: 0 0 1rem;
}

.waves-empty-description {
  font-size: 1rem;
  color: var(--waves-text-secondary);
  margin: 0 0 2rem;
  line-height: 1.6;
}

.waves-empty-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.waves-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: var(--waves-radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
}

.waves-btn-icon {
  width: 16px;
  height: 16px;
}

.waves-btn-primary {
  background: var(--waves-primary-600);
  color: white;
}

.waves-btn-primary:hover {
  background: var(--waves-primary-700);
  transform: translateY(-2px);
  box-shadow: var(--waves-shadow-md);
}

.waves-btn-secondary {
  background: var(--waves-surface-secondary);
  color: var(--waves-text-primary);
  border: 1px solid var(--waves-border-light);
}

.waves-btn-secondary:hover {
  background: var(--waves-surface-primary);
  border-color: var(--waves-primary-300);
  transform: translateY(-2px);
  box-shadow: var(--waves-shadow-md);
}

/* 滚动条样式 */
.waves-table-content::-webkit-scrollbar,
.waves-grid-view::-webkit-scrollbar {
  width: 8px;
}

.waves-table-content::-webkit-scrollbar-track,
.waves-grid-view::-webkit-scrollbar-track {
  background: var(--waves-surface-secondary);
  border-radius: var(--waves-radius-sm);
}

.waves-table-content::-webkit-scrollbar-thumb,
.waves-grid-view::-webkit-scrollbar-thumb {
  background: var(--waves-border-light);
  border-radius: var(--waves-radius-sm);
}

.waves-table-content::-webkit-scrollbar-thumb:hover,
.waves-grid-view::-webkit-scrollbar-thumb:hover {
  background: var(--waves-primary-400);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .waves-grid-content {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 1rem;
  }
}

@media (max-width: 768px) {
  .waves-date-cell {
    display: none;
  }
  
  .waves-size-cell {
    width: 100px;
  }
  
  .waves-action-cell {
    width: 100px;
  }
  
  .waves-grid-content {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
  }
  
  .waves-grid-view {
    padding: 1rem;
  }
  
  .waves-empty-actions {
    flex-direction: column;
    align-items: center;
  }
}

@media (max-width: 480px) {
  .waves-table-header,
  .waves-table-row {
    padding: 0.75rem 1rem;
  }
  
  .waves-name-cell {
    min-width: 150px;
  }
  
  .waves-size-cell {
    width: 80px;
  }
  
  .waves-action-cell {
    width: 80px;
  }
  
  .waves-grid-content {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  }
  
  .waves-card-header,
.waves-card-body {
  padding: 0.75rem;
}
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #ffffff;
  border-radius: 8px;
  width: 340px;
  max-width: calc(100vw - 32px);
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.dialog-title {
  margin: 0 0 8px 0;
  font-weight: 600;
  color: var(--waves-text-primary);
}

.dialog-desc {
  margin: 0 0 12px 0;
  color: var(--waves-text-secondary);
}

.dialog .form-group {
  margin: 12px 0;
}

.dialog .form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.dialog-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.dialog .btn {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--waves-border-light);
  background: var(--waves-surface-secondary);
  color: var(--waves-text-primary);
  transition: all 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  box-shadow: 0 2px 8px rgba(27, 44, 72, 0.12);
}

.dialog .btn:hover {
  background: var(--waves-surface-primary);
  border-color: var(--waves-primary-300);
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(27, 44, 72, 0.16);
}

.dialog .btn.cancel {
  color: var(--waves-text-secondary);
}
</style>
