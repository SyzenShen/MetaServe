<template>
  <div v-if="ncbi.showDialog" class="workspace-modal-overlay" @click="onOverlayClick">
    <div class="ncbi-modal" @click.stop>
      <h3>NCBI Data Download</h3>
      <p class="ncbi-tip">
        Enter an NCBI link (Gene, Protein, SRA, PubMed, etc.) and the system will auto-detect and download.
      </p>
      <input
        v-model="ncbi.url"
        class="ncbi-input"
        placeholder="https://www.ncbi.nlm.nih.gov/..."
        :disabled="ncbi.isSubmitting"
      />
      <p v-if="ncbi.error" class="ncbi-error">{{ ncbi.error }}</p>
      <div class="ncbi-actions">
        <button class="toolbar-btn ghost" @click="ncbi.close" :disabled="ncbi.isSubmitting">Cancel</button>
        <button class="toolbar-btn primary" @click="ncbi.submit" :disabled="ncbi.isSubmitting || !ncbi.url.trim()">
          {{ ncbi.isSubmitting ? 'Downloading…' : 'Start Download' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useNcbiStore } from '../stores/ncbi'

const ncbi = useNcbiStore()

const onOverlayClick = (e) => {
  // 点击遮罩层关闭，但下载中不关闭
  if (!ncbi.isSubmitting) {
    ncbi.close()
  }
}
</script>

<style scoped>
.workspace-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.ncbi-modal {
  width: 560px;
  background: #ffffff;
  border-radius: 10px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.18);
  padding: 20px;
}

.ncbi-modal h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.ncbi-tip {
  margin: 0 0 14px 0;
  font-size: 13px;
  color: #666;
}

.ncbi-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  outline: none;
  transition: all 0.2s ease;
}

.ncbi-input:focus {
  box-shadow: 0 0 0 3px rgba(58, 126, 185, 0.2);
  border-color: rgb(58, 126, 185);
}

.ncbi-error {
  color: #b71c1c;
  margin: 10px 0 0 0;
  font-size: 13px;
}

.ncbi-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.ncbi-actions .toolbar-btn {
  padding: 10px 22px; /* 增大按钮点击区域 */
  font-size: 14px;    /* 增大字体，提升可读性 */
  border-radius: 8px; /* 略微增大圆角 */
}

.toolbar-btn.primary {
  background-color: rgb(58, 126, 185);
  color: #ffffff;
  box-shadow: none; /* 移除主按钮默认阴影 */
  border: none;     /* 去掉边框 */
}

.toolbar-btn.primary:hover {
  background-color: rgb(45, 102, 150);
  box-shadow: none; /* 悬停时不显示阴影 */
  transform: none;  /* 悬停时不位移 */
  border: none;     /* 悬停也不显示边框 */
}

.toolbar-btn.ghost {
  background-color: transparent;
  border: 1px solid var(--border-color);
}
</style>