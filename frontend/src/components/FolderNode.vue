<template>
  <div class="folder-node-container">
    <div 
      class="folder-node"
      :class="{ 
        active: currentFolderId === folder.id,
        'has-children': hasChildren
      }"
      :style="{ paddingLeft: `${(level * 20) + 16}px` }"
      @click="handleClick"
    >
      <!-- 展开/收起图标 -->
      <span 
        v-if="hasChildren"
        class="expand-icon"
        :class="{ expanded: isExpanded }"
        @click.stop="handleToggle"
      >
        ▶
      </span>
      <span v-else class="expand-placeholder"></span>
      

      
      <!-- 文件夹名称 -->
      <span class="folder-name" :title="folder.name">
        {{ folder.name }}<template v-if="folder.organization_name"> · {{ folder.organization_name }}</template>
      </span>
    </div>
    
    <!-- 子文件夹 -->
    <div v-if="isExpanded && hasChildren" class="children">
      <FolderNode
        v-for="child in children"
        :key="child.id"
        :folder="child"
        :current-folder-id="currentFolderId"
        :expanded-folders="expandedFolders"
        :all-folders="allFolders"
        :level="level + 1"
        @navigate="$emit('navigate', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// Props
const props = defineProps({
  folder: {
    type: Object,
    required: true
  },
  currentFolderId: {
    type: [Number, String],
    default: null
  },
  expandedFolders: {
    type: Set,
    required: true
  },
  allFolders: {
    type: Array,
    required: true
  },
  level: {
    type: Number,
    default: 0
  }
})

// Emits
const emit = defineEmits(['navigate', 'toggle'])

// 计算属性
const isExpanded = computed(() => {
  return props.expandedFolders.has(props.folder.id)
})

const children = computed(() => {
  // 从allFolders中获取当前文件夹的子文件夹
  return props.allFolders.filter(f => f.parent === props.folder.id)
})

const hasChildren = computed(() => {
  return children.value.length > 0
})

// 方法
const handleClick = () => {
  emit('navigate', props.folder.id)
}

const handleToggle = () => {
  emit('toggle', props.folder.id)
}
</script>

<style scoped>
.folder-node-container {
  width: 100%;
}

.folder-node {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  user-select: none;
  min-height: 32px;
  color: var(--text-muted); /* 未选中更浅灰 */
}

.folder-node:hover {
  background-color: #f3f2f1; /* 与 .root-node:hover 一致 */
  color: #323130; /* 悬停为深灰，保持可点击反馈 */
}

.folder-node.active {
  background-color: #ffffff; /* 选中白底 */
  color: var(--text-primary); /* 选中为中性主文本色，不再蓝色 */
  border-radius: var(--waves-radius-sm);
  margin: 8px 8px 12px; /* 与 All Files 一致，避免阴影裁切 */
  /* 与 All Files 同步：自然下投阴影，避免四周发光和裁切感 */
  box-shadow:
    0 2px 6px rgba(27, 44, 72, 0.14),
    0 8px 20px rgba(27, 44, 72, 0.12);
  font-weight: 600; /* 选中加粗 */
}

.folder-node.active:hover {
  background-color: #ffffff;
  /* 悬停轻微增强下投阴影，保持自然 */
  box-shadow:
    0 4px 8px rgba(27, 44, 72, 0.16),
    0 10px 24px rgba(27, 44, 72, 0.14);
}

.expand-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 4px;
  font-size: 10px;
  transition: transform 0.2s;
  cursor: pointer;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.expand-placeholder {
  width: 16px;
  margin-right: 4px;
}

.folder-icon {
  margin-right: 8px;
  font-size: 14px;
}

.folder-name {
  flex: 1;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.children {
  width: 100%;
}

/* 活动状态下的图标颜色 */
.folder-node.active .expand-icon,
.folder-node.active .folder-icon {
  color: var(--text-primary); /* 图标颜色与文本一致，非蓝色 */
}
</style>
