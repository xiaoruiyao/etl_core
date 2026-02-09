<template>
  <div class="hierarchy-node">
    <div 
      class="node-content" 
      :class="{ active: activeId === node.id }"
      @click="toggle"
    >
      <span class="tree-toggle" @click.stop="expanded = !expanded" v-if="hasChildren">
        {{ expanded ? '▼' : '▶' }}
      </span>
      <span class="tree-spacer" v-else></span>
      
      <span class="node-icon">{{ getIcon(node.type) }}</span>
      <span class="node-label">{{ node.label }}</span>
    </div>
    
    <div class="node-children" v-if="expanded && hasChildren">
      <HierarchyNode 
        v-for="child in node.children" 
        :key="child.id" 
        :node="child" 
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  node: Object,
  activeId: [Number, String]
})

const emit = defineEmits(['select'])

const expanded = ref(true)

const hasChildren = computed(() => {
  if (props.node.children && props.node.children.length > 0) return true
  // Allow expanding devices/PLCs to show points
  if (['DEVICE', 'PLC'].includes(props.node.type)) return true
  return false
})

const toggle = async () => {
    // If expanding a device without children, ask parent to load
    if (!expanded.value && 
        ['DEVICE', 'PLC'].includes(props.node.type) && 
        (!props.node.children || props.node.children.length === 0)) {
       emit('expand', props.node)
    }
    
    // Toggle functionality
    if (hasChildren.value) {
        expanded.value = !expanded.value
    }
    
    emit('select', props.node)
}

const getIcon = (type) => {
  const map = {
    'FACTORY': '🏭',
    'WORKSHOP': '🏗️',
    'LINE': '🛤️',
    'STATION': '📍',
    'PLC': '🤖',
    'DEVICE': '🔧'
  }
  return map[type] || '📄'
}
</script>

<style scoped>
.hierarchy-node {
  display: flex;
  flex-direction: column;
}

.node-content {
  display: flex;
  align-items: center;
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.node-content:hover {
  background: rgba(255,255,255,0.05);
}

.node-content.active {
  background: rgba(59, 130, 246, 0.2);
  color: var(--color-blue);
}

.tree-toggle {
  width: 20px;
  font-size: 10px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tree-spacer { width: 20px; }

.node-icon { margin-right: 6px; font-size: 14px; }
.node-label { font-size: 13px; font-weight: 500; }

.node-children {
  padding-left: 16px;
  border-left: 1px solid rgba(255,255,255,0.05);
  margin-left: 9px;
}
</style>
