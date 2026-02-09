<template>
  <div class="layout-sidebar">
    <div class="sidebar-header">
       <h3>资产视图</h3>
    </div>
    <div class="tree-container">
      <div v-if="loadingTree" class="loading-text">加载中...</div>
      <div v-else class="tree-root">
         <!-- Root Nodes -->
         <HierarchyNode 
           v-for="node in structureTree" 
           :key="node.id" 
           :node="node" 
           :active-id="activeId"
           @select="handleNodeSelect"
           @expand="handleNodeExpand"
         />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import HierarchyNode from './HierarchyNode.vue'
import { getStructureTree, getPoints } from '../../api'

const props = defineProps({
  activeId: [Number, String]
})

const emit = defineEmits(['select'])

const loadingTree = ref(true)
const structureTree = ref([])

// Load Tree
const loadTree = async () => {
  try {
    loadingTree.value = true
    structureTree.value = await getStructureTree()
  } finally {
    loadingTree.value = false
  }
}

const handleNodeSelect = (node) => {
  emit('select', node)
}

// Lazy Load Points into Tree (Consistent with Devices.vue)
const handleNodeExpand = async (node) => {
    if (node.childrenLoaded) return
    
    try {
        let points = []
        if (node.type === 'DEVICE') {
           points = await getPoints({ structure_id: node.id })
        } else if (node.type === 'PLC') {
           points = await getPoints({ plc_id: node.id })
        }
        
        if (points.length > 0) {
            // Convert points to Tree Nodes (Folders + Files)
            const pointNodes = buildPointTree(points, node.id)
            if (!node.children) node.children = []
            node.children.push(...pointNodes)
        }
        
        node.childrenLoaded = true
    } catch (e) {
        console.error("Failed to load points for node", node.label, e)
    }
}

// Convert flat list of points with group_path to nested tree nodes
const buildPointTree = (points, parentId) => {
    const root = { children: [] }
    
    points.forEach(p => {
        const pathParts = p.group_path ? p.group_path.split('/').filter(Boolean) : []
        let currentLevel = root
        
        // Build folders
        pathParts.forEach((part, index) => {
             let existingFolder = currentLevel.children.find(c => c.label === part && c.type === 'FOLDER')
             if (!existingFolder) {
                 existingFolder = {
                     id: `folder-${parentId}-${part}-${index}-${Math.random()}`, // Unique ID
                     label: part,
                     type: 'FOLDER',
                     children: [],
                     isLeaf: false
                 }
                 currentLevel.children.push(existingFolder)
             }
             currentLevel = existingFolder
        })
        
        // Add File
        currentLevel.children.push({
            id: `point-${p.id}`,
            label: p.point_name,
            type: 'POINT', // Custom type
            data_type: p.data_type,
            uri: p.point_uri,
            isLeaf: true
        })
    })
    
    return root.children
}

onMounted(() => {
  loadTree()
})
</script>

<style scoped>
.layout-sidebar {
  width: 300px;
  background: var(--glass-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  height: 100%; /* Important for fit */
}

.sidebar-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-color);
}
.sidebar-header h3 { margin: 0; font-size: var(--font-size-md); }

.tree-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

.tree-root { display: flex; flex-direction: column; gap: 2px; }
.loading-text { padding: 20px; color: var(--text-secondary); text-align: center; }
</style>
