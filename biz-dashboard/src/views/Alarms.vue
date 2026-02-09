<template>
  <div class="alarms-page">
    <AppHeader title="报警记录" :subtitle="`共 ${total} 条报警`" />
    
    <div class="split-layout">
      <!-- Sidebar -->
      <HierarchySidebar 
        :active-id="filters.structure_id" 
        @select="handleNodeSelect" 
      />
      
      <!-- Main Content -->
      <div class="layout-main">
        <div class="main-header" v-if="activeNode">
             <div class="header-title">
               <h2>{{ activeNode.label }}</h2>
               <AppBadge :type="getLevelBadge(activeNode.type)">{{ activeNode.type }}</AppBadge>
             </div>
             <div class="header-sub">
                筛选范围: {{ activeNode.path }}
             </div>
        </div>

        <div class="alarms-content">
          <AppCard>
            <table class="alarms-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>级别</th>
                  <th>错误码</th>
                  <th>报警信息</th>
                  <th>关联结果</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="alarm in alarms" :key="alarm.id">
                  <td class="col-id">{{ alarm.id }}</td>
                  <td>
                    <AppBadge :type="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'" size="sm">
                      {{ alarm.alarm_level }}
                    </AppBadge>
                  </td>
                  <td class="col-code">{{ alarm.alarm_code }}</td>
                  <td class="col-msg">{{ alarm.alarm_msg }}</td>
                  <td>
                    <a @click="goToResult(alarm.result_id)" class="result-link">
                      #{{ alarm.result_id }}
                    </a>
                  </td>
                  <td class="col-time">{{ formatTime(alarm.create_time) }}</td>
                </tr>
              </tbody>
            </table>
            
            <div v-if="alarms.length === 0" class="empty-state">
              暂无报警记录
            </div>
            
            <div class="pagination">
              <AppButton 
                variant="secondary" 
                size="sm" 
                :disabled="page <= 1"
                @click="page--; loadAlarms()"
              >
                上一页
              </AppButton>
              <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
              <AppButton 
                variant="secondary" 
                size="sm"
                :disabled="page >= totalPages"
                @click="page++; loadAlarms()"
              >
                下一页
              </AppButton>
            </div>
          </AppCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/layout/AppHeader.vue'
import AppCard from '../components/common/AppCard.vue'
import AppBadge from '../components/common/AppBadge.vue'
import AppButton from '../components/common/AppButton.vue'
import HierarchySidebar from '../components/common/HierarchySidebar.vue'
import { getAlarms } from '../api'

const router = useRouter()
const alarms = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const activeNode = ref(null)
const filters = ref({
  structure_id: null
})

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const goToResult = (id) => {
  router.push(`/results/${id}`)
}

const getLevelBadge = (type) => {
  const map = {
    'FACTORY': 'primary',
    'WORKSHOP': 'primary',
    'LINE': 'success',
    'STATION': 'warning',
    'PLC': 'error',
    'DEVICE': 'info'
  }
  return map[type] || 'info'
}

const handleNodeSelect = (node) => {
  activeNode.value = node
  filters.value.structure_id = node.id
  page.value = 1
  loadAlarms()
}

const loadAlarms = async () => {
  try {
    const data = await getAlarms({
      page: page.value,
      page_size: pageSize,
      structure_id: filters.value.structure_id || undefined
    })
    alarms.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('Failed to load alarms:', e)
  }
}

onMounted(loadAlarms)
</script>

<style scoped>
.alarms-page {
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

.layout-main {
  flex: 1;
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-header {
  padding: var(--space-4);
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-title { display: flex; align-items: center; gap: 8px; }
.header-title h2 { margin: 0; font-size: 16px; }
.header-sub { font-family: monospace; font-size: 12px; color: var(--text-tertiary); }

.alarms-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

.alarms-table {
  width: 100%;
  border-collapse: collapse;
}

.alarms-table th,
.alarms-table td {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.alarms-table th {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  background: rgba(255,255,255,0.02);
}

.alarms-table td {
  font-size: var(--font-size-sm);
}

.col-id {
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.col-code {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.col-msg {
  color: var(--text-primary);
  max-width: 300px;
}

.col-time {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
}

.result-link {
  color: var(--color-blue);
  cursor: pointer;
}

.result-link:hover {
  text-decoration: underline;
}

.empty-state {
  padding: var(--space-12);
  text-align: center;
  color: var(--text-secondary);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.page-info {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
