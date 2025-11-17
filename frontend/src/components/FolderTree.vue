<template>
  <div class="folder-tree">
    <div class="tree-content">
      <!-- 根目录 -->
  <div 
    class="tree-node root-node"
    :class="{ active: currentFolderId === null }"
    @click="navigateToRoot"
  >
    <span class="node-label">All Files</span>
  </div>
      
      <!-- 文件夹树 -->
      <div class="folder-nodes">
        <FolderNode
          v-for="folder in rootFolders"
          :key="folder.id"
          :folder="folder"
          :current-folder-id="currentFolderId"
          :expanded-folders="expandedFolders"
          :all-folders="allFolders"
          @navigate="handleNavigate"
          @toggle="handleToggle"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useFilesStore } from '../stores/files'
import FolderNode from './FolderNode.vue'

const filesStore = useFilesStore()

// 响应式数据
const expandedFolders = ref(new Set())
const allFolders = ref([]) // 存储所有文件夹

// 计算属性
const currentFolderId = computed(() => filesStore.currentFolderId)
const rootFolders = computed(() => {
  // 获取根级文件夹（没有父文件夹的）
  return allFolders.value.filter(folder => !folder.parent)
})

// 方法
const navigateToRoot = () => {
  filesStore.navigateToFolder(null)
}

const handleNavigate = (folderId) => {
  filesStore.navigateToFolder(folderId)
}

const handleToggle = (folderId) => {
  if (expandedFolders.value.has(folderId)) {
    expandedFolders.value.delete(folderId)
  } else {
    expandedFolders.value.add(folderId)
  }
}

// 加载所有文件夹
const loadAllFolders = async () => {
  try {
    const response = await fetch('/api/files/folders/all/', {
      headers: {
        'Authorization': `Token ${localStorage.getItem('token')}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      allFolders.value = data.folders || []
    } else {
      console.error('加载文件夹失败:', response.statusText)
    }
  } catch (error) {
    console.error('加载文件夹失败:', error)
  }
}

// 智能展开到当前文件夹的路径，同时关闭不需要的文件夹
const expandToCurrentFolder = () => {
  // 如果没有当前文件夹，清空所有展开状态
  if (!currentFolderId.value) {
    expandedFolders.value.clear()
    return
  }
  
  // 找到当前文件夹
  const currentFolder = allFolders.value.find(f => f.id === currentFolderId.value)
  if (!currentFolder) {
    expandedFolders.value.clear()
    return
  }
  
  // 计算需要展开的路径（从根到当前文件夹的父级路径）
  const pathToExpand = new Set()
  let folder = currentFolder
  
  while (folder && folder.parent) {
    pathToExpand.add(folder.parent)
    folder = allFolders.value.find(f => f.id === folder.parent)
  }
  
  // 只保留需要展开的文件夹，关闭其他所有文件夹
  expandedFolders.value = pathToExpand
}

// 监听当前文件夹变化，自动展开路径
watch(currentFolderId, () => {
  expandToCurrentFolder()
}, { immediate: true })

// 监听allFolders变化，确保在数据加载后展开路径
watch(allFolders, () => {
  expandToCurrentFolder()
}, { immediate: true })

// 生命周期
onMounted(async () => {
  // 加载所有文件夹
  await loadAllFolders()
  // 初始化时加载当前目录的文件
  await filesStore.fetchFiles(currentFolderId.value)
})
</script>

<style scoped>
.folder-tree {
  width: 250px;
  height: 100%;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.tree-node {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  color: #605e5c;
  border-radius: var(--waves-radius-sm);
  margin: 1px 4px;
}

.tree-node:hover {
  background-color: #f3f2f1;
  color: #323130;
}


/* 根节点 All Files：未选中浅灰，选中白底蓝框 */
.root-node {
  font-weight: 400; /* 未选中不加粗 */
  margin: 8px 8px 12px; /* 留出空间避免阴影被裁切 */
  color: var(--text-muted); /* 未选中更浅的中性灰 */
  background: transparent; /* 未选中保持与普通项一致（无底色） */
  border: none; /* 无边框 */
  border-radius: var(--waves-radius-sm);
  padding: 6px 8px; /* 与普通项保持一致 */
}
.root-node:hover {
  background: #f3f2f1; /* 与 .tree-node:hover 一致 */
  color: #323130; /* 悬停为深灰 */
}
.root-node.active {
  background: #ffffff; /* 选中白底 */
  color: var(--text-primary); /* 选中文本改为中性主文本色，不再蓝色 */
  border: none; /* 无边框 */
  /* 自然的下投阴影，减少四周发光感，避免裁切不适 */
  box-shadow:
    0 2px 6px rgba(27, 44, 72, 0.14),
    0 8px 20px rgba(27, 44, 72, 0.12);
  font-weight: 600; /* 选中加粗 */
}

.root-node.active:hover {
  background: #ffffff;
  box-shadow:
    0 4px 8px rgba(27, 44, 72, 0.16),
    0 10px 24px rgba(27, 44, 72, 0.14);
}

/* 去除旧的仅文字颜色强调样式，改为按钮式风格 */

.node-icon {
  margin-right: 8px;
  font-size: 16px;
}

.node-label {
  flex: 1;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.folder-nodes {
  padding-left: 0;
}

/* 滚动条样式 */
.tree-content::-webkit-scrollbar {
  width: 6px;
}

.tree-content::-webkit-scrollbar-track {
  background: #ffffff;
}

.tree-content::-webkit-scrollbar-thumb {
  background: #c8c6c4;
  border-radius: var(--waves-radius-sm);
}

.tree-content::-webkit-scrollbar-thumb:hover {
  background: #a19f9d;
}
</style>
