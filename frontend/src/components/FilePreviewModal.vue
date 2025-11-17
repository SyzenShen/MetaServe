<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-container" @click.stop>
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="file-info">
          <h2>{{ file.title || file.original_filename }}</h2>
          <div class="file-meta">
            <span class="format">{{ file.file_format }}</span>
            <span class="size">{{ formatFileSize(file.file_size) }}</span>
            <span class="date">{{ formatDate(file.uploaded_at) }}</span>
          </div>
        </div>
        <button @click="closeModal" class="close-btn">✕</button>
      </div>

      <!-- Modal Content -->
      <div class="modal-content">
        <!-- Loading State -->
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Loading preview...</p>
        </div>

        <!-- Preview Content -->
        <div v-else-if="previewData" class="preview-content">
          <!-- Text Preview -->
          <div v-if="previewData.type === 'text'" class="text-preview">
            <div class="preview-header">
              <h3>Text Preview</h3>
              <div class="text-stats">
                <span>{{ previewData.total_lines }} lines</span>
                <span>{{ previewData.preview_chars }}/{{ previewData.total_chars }} chars</span>
              </div>
            </div>
            <pre class="text-content">{{ previewData.content }}</pre>
          </div>

          <!-- Sequence Preview -->
          <div v-else-if="previewData.type === 'sequence'" class="sequence-preview">
            <div class="preview-header">
              <h3>{{ previewData.format }} Sequence Preview</h3>
              <div class="sequence-stats">
                <span>First {{ previewData.total_lines_preview }} lines</span>
              </div>
            </div>
            <pre class="sequence-content">{{ previewData.content }}</pre>
          </div>

          <!-- PDF Preview -->
          <div v-else-if="previewData.type === 'pdf_text'" class="pdf-preview">
            <div class="preview-header">
              <h3>PDF Text Preview</h3>
              <div class="pdf-stats">
                <span>{{ previewData.page_count }} pages</span>
                <span>Source: {{ previewData.source }}</span>
              </div>
            </div>
            <div class="pdf-content">{{ previewData.content }}</div>
          </div>

          <!-- PDF Info -->
          <div v-else-if="previewData.type === 'pdf_info'" class="pdf-info">
            <div class="preview-header">
              <h3>PDF File Info</h3>
            </div>
            <p class="pdf-message">{{ previewData.message }}</p>
            <div v-if="previewData.metadata" class="metadata-display">
              <h4>Metadata:</h4>
              <pre>{{ JSON.stringify(previewData.metadata, null, 2) }}</pre>
            </div>
            <a :href="previewData.download_url" class="download-link" target="_blank">
              Download to view full content
            </a>
          </div>

          <!-- Metadata Only -->
          <div v-else-if="previewData.type === 'metadata_only'" class="metadata-only">
            <div class="preview-header">
              <h3>File Info</h3>
            </div>
            <p class="metadata-message">{{ previewData.message }}</p>
          </div>

          <!-- Error State -->
          <div v-else-if="previewData.type === 'error'" class="error-preview">
            <div class="error-icon"></div>
            <h3>Preview Failed</h3>
            <p>{{ previewData.message }}</p>
          </div>
        </div>

          <!-- Error State -->
        <div v-else-if="error" class="error-state">
          <div class="error-icon"></div>
          <h3>Load Failed</h3>
          <p>{{ error }}</p>
        </div>
      </div>

      <!-- File Details -->
      <div class="file-details">
        <h3>File Details</h3>
        <div class="details-grid">
          <div class="detail-item">
            <label>Project:</label>
            <span>{{ file.project }}</span>
          </div>
          <div class="detail-item">
            <label>Uploader:</label>
            <span>{{ file.uploader }}</span>
          </div>
          <div class="detail-item">
            <label>Document Type:</label>
            <span>{{ file.document_type }}</span>
          </div>
          <div class="detail-item">
            <label>Access Level:</label>
            <span>{{ file.access_level }}</span>
          </div>
          <div v-if="file.organism" class="detail-item">
            <label>Organism:</label>
            <span>{{ file.organism }}</span>
          </div>
          <div v-if="file.experiment_type" class="detail-item">
            <label>Experiment Type:</label>
            <span>{{ file.experiment_type }}</span>
          </div>
          <div v-if="file.qc_status" class="detail-item">
            <label>QC Status:</label>
            <span>{{ file.qc_status }}</span>
          </div>
          <div v-if="file.checksum" class="detail-item">
            <label>Checksum:</label>
            <span class="checksum">{{ file.checksum }}</span>
          </div>
        </div>
        
        <div v-if="file.description" class="description-section">
          <label>Description:</label>
          <p>{{ file.description }}</p>
        </div>
        
        <div v-if="file.tags_list && file.tags_list.length > 0" class="tags-section">
          <label>Tags:</label>
          <div class="tags">
            <span v-for="tag in file.tags_list" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </div>

        <!-- Extracted Metadata -->
        <div v-if="file.extracted_metadata && Object.keys(file.extracted_metadata).length > 0" class="extracted-metadata">
          <h4>Automatically Extracted Metadata</h4>
          <div class="metadata-content">
            <pre>{{ JSON.stringify(file.extracted_metadata, null, 2) }}</pre>
          </div>
        </div>
      </div>

      <!-- Modal Footer Actions -->
      <div class="modal-footer">
        <button @click="downloadFile" class="action-btn download-btn">
          Download
        </button>
        <button @click="closeModal" class="action-btn close-btn">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useFilesStore } from '../stores/files'

export default {
  name: 'FilePreviewModal',
  props: {
    file: {
      type: Object,
      required: true
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const filesStore = useFilesStore()
    
    const isLoading = ref(true)
    const previewData = ref(null)
    const error = ref(null)
    
    const closeModal = () => {
      emit('close')
    }
    
    const loadPreview = async () => {
      try {
        isLoading.value = true
        error.value = null
        
        const response = await filesStore.getFilePreview(props.file.id)
        previewData.value = response.preview
        
      } catch (err) {
        console.error('加载预览失败:', err)
        error.value = err.message || '加载预览失败'
      } finally {
        isLoading.value = false
      }
    }
    
    const downloadFile = async () => {
      try {
        await filesStore.downloadFile(props.file.id, props.file.original_filename)
      } catch (err) {
        console.error('下载失败:', err)
      }
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
    
    onMounted(() => {
      loadPreview()
    })
    
    return {
      isLoading,
      previewData,
      error,
      closeModal,
      downloadFile,
      formatFileSize,
      formatDate
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-container {
  background: white;
  border-radius: 12px;
  max-width: 90vw;
  max-height: 90vh;
  width: 1000px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  background: #f8f9fa;
}

.file-info h2 {
  margin: 0 0 8px 0;
  color: #2c3e50;
  font-size: 1.4rem;
}

.file-meta {
  display: flex;
  gap: 15px;
  color: #6c757d;
  font-size: 0.9rem;
}

.format {
  background: #e9ecef;
  padding: 2px 8px;
  border-radius: 4px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
  padding: 5px;
  border-radius: 4px;
  transition: background 0.3s;
}

.close-btn:hover {
  background: #e9ecef;
}

.modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  min-height: 300px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #6c757d;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e9ecef;
}

.preview-header h3 {
  margin: 0;
  color: #2c3e50;
}

.text-stats, .sequence-stats, .pdf-stats {
  display: flex;
  gap: 15px;
  color: #6c757d;
  font-size: 0.9rem;
}

.text-content, .sequence-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.4;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.pdf-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

.pdf-message, .metadata-message {
  color: #6c757d;
  font-style: italic;
  margin-bottom: 15px;
}

.download-link {
  display: inline-block;
  padding: 10px 20px;
  background: #3498db;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.3s;
}

.download-link:hover {
  background: #2980b9;
}

.metadata-display, .metadata-content {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-top: 15px;
}

.metadata-display h4 {
  margin-top: 0;
  color: #495057;
}

.metadata-display pre, .metadata-content pre {
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.4;
  margin: 0;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.error-preview, .error-state {
  text-align: center;
  padding: 40px 20px;
  color: #e74c3c;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 15px;
}

.file-details {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.file-details h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-item label {
  font-weight: 600;
  color: #495057;
  font-size: 0.9rem;
}

.detail-item span {
  color: #6c757d;
}

.checksum {
  font-family: 'Courier New', monospace;
  font-size: 0.8rem;
  word-break: break-all;
}

.description-section, .tags-section {
  margin-bottom: 20px;
}

.description-section label, .tags-section label {
  display: block;
  font-weight: 600;
  color: #495057;
  margin-bottom: 8px;
}

.description-section p {
  color: #6c757d;
  line-height: 1.5;
  margin: 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  background: #e9ecef;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.8rem;
  color: #495057;
}

.extracted-metadata {
  margin-top: 20px;
}

.extracted-metadata h4 {
  margin-bottom: 10px;
  color: #495057;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  padding: 20px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.action-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.3s;
}

.download-btn {
  background: #28a745;
  color: white;
}

.download-btn:hover {
  background: #218838;
}

.modal-footer .close-btn {
  background: #6c757d;
  color: white;
}

.modal-footer .close-btn:hover {
  background: #5a6268;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .modal-container {
    width: 95vw;
    height: 95vh;
  }
  
  .modal-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .file-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .details-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-footer {
    flex-direction: column;
  }
}
</style>