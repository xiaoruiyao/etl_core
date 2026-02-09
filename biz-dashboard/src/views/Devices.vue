<template>
  <div class="devices-page">
    <AppHeader title="设备层级与点位" subtitle="设备资产管理与时序点位浏览" />
    
    <div class="split-layout">
      <!-- Left: Hierarchy Tree -->
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
               :active-id="activeNodeId"
               @select="handleNodeSelect"
               @expand="handleNodeExpand"
             />
          </div>
        </div>
      </div>
      
      <!-- Right: Main Content (Device Grid Only) -->
      <div class="layout-main">
        <div class="content-header">
             <div class="header-title">
               <h2>{{ activeNode?.label || '全部设备' }}</h2>
               <AppBadge v-if="activeNode" :type="getLevelBadge(activeNode.type)">{{ activeNode.type }}</AppBadge>
             </div>
             <div class="header-meta" v-if="activeNode?.path">
                Path: {{ activeNode.path }}
             </div>
             
             <!-- Craft Filter Tabs -->
             <div class="craft-tabs">
                <button 
                  v-for="craft in craftTypes" 
                  :key="craft.value"
                  class="craft-tab"
                  :class="{ active: selectedCraft === craft.value }"
                  @click="selectedCraft = craft.value"
                >
                  <span class="craft-icon">{{ craft.icon }}</span>
                  <span class="craft-name">{{ craft.label }}</span>
                  <span class="craft-count">{{ craft.count }}</span>
                </button>
             </div>
        </div>

        <div class="devices-view">
             
             <transition-group name="device" tag="div" class="devices-grid">
                <div 
                  v-for="(device, index) in filteredDevices" 
                  :key="device.device_name"
                  class="device-card"
                  :style="{ '--delay': index * 0.05 + 's' }"
                  @click="goToDeviceDetail(device)"
                >
                  <div class="device-header">
                    <h3 class="device-name">{{ device.device_name }}</h3>
                     <div class="device-status" :class="device.status"></div>
                  </div>
                  
                  <div class="device-stats" v-if="device.total_count > 0">
                    <div class="stat-item">
                      <span class="stat-label">总产量</span>
                      <span class="stat-value">{{ device.total_count?.toLocaleString() }}</span>
                    </div>
                    <div class="stat-item ok">
                      <span class="stat-label">合格率</span>
                      <span class="stat-value">{{ device.ok_rate?.toFixed(1) }}%</span>
                    </div>
                  </div>
                  <div class="device-stats" v-else>
                     <div class="stat-item">
                        <span class="stat-label">设备类型</span>
                        <span class="stat-value" style="font-size: 14px; color: var(--text-secondary)">{{ device.craft_type || '非生产设备' }}</span>
                     </div>
                  </div>
                  
                  <div class="device-footer">
                     <span class="device-craft">{{ device.craft_type }}</span>
                  </div>
                </div>
             </transition-group>
             
             <div v-if="filteredDevices.length === 0" class="empty-state">
                <div class="empty-icon">🔍</div>
                <div>未找到相关设备</div>
             </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/layout/AppHeader.vue'
import AppBadge from '../components/common/AppBadge.vue'
import HierarchyNode from '../components/common/HierarchyNode.vue'
import { getStructureTree, getPoints, getDevices } from '../api'

const router = useRouter()
const loadingTree = ref(true)
const structureTree = ref([])
const activeNodeId = ref(null)
const activeNode = ref(null)

// Data
const allDevicesStats = ref([]) 
const selectedCraft = ref('all')

// Load Initial Data
const loadDat = async () => {
  try {
    loadingTree.value = true
    const [treeData, devicesData] = await Promise.all([
      getStructureTree(),
      getDevices()
    ])
    structureTree.value = treeData
    allDevicesStats.value = devicesData.items || []
  } finally {
    loadingTree.value = false
  }
}

// Logic to find all device names under a node
const getDeviceNamesUnderNode = (node) => {
  let names = []
  if (node.device_name) names.push(node.device_name)
  if (node.children) {
    node.children.forEach(child => {
      // Only traverse structure nodes, not POINT/FOLDER nodes
      if (['FACTORY', 'WORKSHOP', 'LINE', 'STATION', 'PLC', 'DEVICE'].includes(child.type)) {
          names = names.concat(getDeviceNamesUnderNode(child))
      }
    })
  }
  return names
}

// Filtered Devices Logic
const validDevices = computed(() => {
    // 1. Filter by Hierarchy Scope
    let scopeDevices = allDevicesStats.value
    if (activeNode.value) {
        // If it's a Point/Folder node, user likely wants to see the device it belongs to
        // But simplifying: just take the device names in scope
        const targetNames = new Set(getDeviceNamesUnderNode(activeNode.value))
        
        // If targetNames is empty (e.g. leaf point), maybe climb up?
        // For now, if empty result, just show nothing.
        scopeDevices = allDevicesStats.value.filter(d => targetNames.has(d.device_name))
    }
    return scopeDevices
})

const craftTypes = computed(() => {
  const crafts = {}
  validDevices.value.forEach(d => {
    const c = d.craft_type || 'Unknown'
    if (!crafts[c]) crafts[c] = 0
    crafts[c]++
  })
  
  const items = [
    { value: 'all', label: '全部', icon: '🔧', count: validDevices.value.length }
  ]
  
  Object.entries(crafts).forEach(([name, count]) => {
    items.push({
      value: name,
      label: name,
      icon: name.includes('FDS') ? '⚙️' : name.includes('SPR') ? '🔩' : '🛠️',
      count
    })
  })
  return items
})

const filteredDevices = computed(() => {
  let list = validDevices.value
  if (selectedCraft.value !== 'all') {
      list = list.filter(d => d.craft_type === selectedCraft.value)
  }
  return list
})

const handleNodeSelect = async (node) => {
  activeNodeId.value = node.id
  activeNode.value = node
}

// Lazy Load Points into Tree
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

const goToDeviceDetail = (device) => {
  router.push(`/devices/${encodeURIComponent(device.device_name)}`)
}

const getLevelBadge = (type) => {
  const map = {
    'FACTORY': 'primary',
    'WORKSHOP': 'primary',
    'LINE': 'success',
    'STATION': 'warning',
    'PLC': 'error',
    'DEVICE': 'info',
    'FOLDER': 'warning',
    'POINT': 'success'
  }
  return map[type] || 'info'
}

onMounted(() => {
  loadDat()
})
</script>

<style scoped>
.devices-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  padding: 0 var(--space-6) var(--space-6);
  gap: var(--space-4);
}

.layout-sidebar {
  width: 320px;
  background: var(--glass-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
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

.layout-main {
  flex: 1;
  background: var(--glass-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
}

.content-header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-color);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.header-title h2 { margin: 0; font-size: var(--font-size-lg); }

.header-meta {
  font-family: monospace;
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  margin-bottom: var(--space-4);
}

/* Craft Tabs */
.craft-tabs {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
}

.craft-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.craft-tab:hover { border-color: rgba(255,255,255,0.2); color: var(--text-primary); }
.craft-tab.active { background: var(--gradient-primary); border-color: transparent; color: white; }

.craft-count { background: rgba(255,255,255,0.2); padding: 1px 6px; border-radius: 10px; font-size: 10px; }

/* Devices Grid View */
.devices-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  overflow-y: auto;
}

.devices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.device-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  cursor: pointer;
  transition: all 0.2s;
  animation: slideUp 0.3s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
  transform: translateY(10px);
}
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }

.device-card:hover { border-color: var(--color-primary); background: rgba(59, 130, 246, 0.05); }

.device-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-3); }
.device-name { margin: 0; font-size: var(--font-size-md); font-weight: 600; color: var(--text-primary); }
.device-status { width: 8px; height: 8px; border-radius: 50%; background: var(--color-success); box-shadow: 0 0 5px var(--color-success); }

.device-stats { display: flex; gap: var(--space-3); margin-bottom: var(--space-3); }
.stat-item { text-align: center; flex: 1; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 4px; }
.stat-value { display: block; font-weight: bold; color: var(--text-primary); }
.stat-label { font-size: 10px; color: var(--text-tertiary); }
.stat-item.ok .stat-value { color: var(--color-success); }

.device-footer { display: flex; justify-content: flex-end; font-size: 11px; color: var(--text-tertiary); }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  padding: var(--space-12);
}
.empty-icon { font-size: 48px; margin-bottom: var(--space-4); opacity: 0.5; }

.tree-root { display: flex; flex-direction: column; gap: 2px; }
.loading-text { padding: 20px; color: var(--text-secondary); text-align: center; }
</style>
