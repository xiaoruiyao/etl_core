<template>
  <div class="results-page">
    <AppHeader title="结果列表" :subtitle="`共 ${total} 条记录`">
      <div class="filters">
        <select v-model="filters.craft_type" class="filter-select" @change="loadResults">
          <option value="">全部工艺</option>
          <option value="FDS_DEFAULT">FDS</option>
          <option value="SPR">SPR</option>
        </select>
        <select v-model="filters.status" class="filter-select" @change="loadResults">
          <option value="">全部状态</option>
          <option value="1">OK</option>
          <option value="0">NOK</option>
        </select>
      </div>
    </AppHeader>
    
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

        <div class="results-content">
          <AppCard>
            <table class="results-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>设备</th>
                  <th>BSN</th>
                  <th>工艺</th>
                  <th>状态</th>
                  <th>关键值</th>
                  <th>周期</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="result in results" 
                  :key="result.id"
                  @click="goToDetail(result.id)"
                  class="clickable"
                >
                  <td class="col-id">{{ result.id }}</td>
                  <td>{{ result.device_name }}</td>
                  <td>{{ result.bsn || '-' }}</td>
                  <td>
                    <AppBadge type="info" size="sm">{{ result.craft_type }}</AppBadge>
                  </td>
                  <td>
                    <AppBadge :type="getStatusType(result.result_status)" size="sm">
                      {{ getStatusText(result.result_status) }}
                    </AppBadge>
                  </td>
                  <td>{{ result.key_value?.toFixed(2) || '-' }}</td>
                  <td>{{ result.cycle_time?.toFixed(3) }}s</td>
                  <td class="col-time">{{ formatTime(result.start_time) }}</td>
                </tr>
              </tbody>
            </table>
            
            <div v-if="results.length === 0" class="empty-state">
              暂无数据
            </div>
            
            <!-- Pagination -->
            <div class="pagination">
              <AppButton 
                variant="secondary" 
                size="sm" 
                :disabled="page <= 1"
                @click="page--; loadResults()"
              >
                上一页
              </AppButton>
              <span class="page-info">第 {{ page }} / {{ totalPages }} 页</span>
              <AppButton 
                variant="secondary" 
                size="sm"
                :disabled="page >= totalPages"
                @click="page++; loadResults()"
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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/layout/AppHeader.vue'
import AppCard from '../components/common/AppCard.vue'
import AppBadge from '../components/common/AppBadge.vue'
import AppButton from '../components/common/AppButton.vue'
import HierarchySidebar from '../components/common/HierarchySidebar.vue'
import { getResults } from '../api'

const router = useRouter()
const results = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const activeNode = ref(null)

const filters = ref({
  craft_type: '',
  status: '',
  structure_id: null
})

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const getStatusType = (status) => {
  if (status === 1) return 'success'
  if (status === 0) return 'error'
  return 'warning'
}

const getStatusText = (status) => {
  if (status === 1) return 'OK'
  if (status === 0) return 'NOK'
  return 'Warn'
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

const handleNodeSelect = (node) => {
  activeNode.value = node
  filters.value.structure_id = node.id
  page.value = 1
  loadResults()
}

const goToDetail = (id) => {
  router.push(`/results/${id}`)
}

const loadResults = async () => {
  try {
    const data = await getResults({
      page: page.value,
      page_size: pageSize,
      craft_type: filters.value.craft_type || undefined,
      status: filters.value.status || undefined,
      structure_id: filters.value.structure_id || undefined
    })
    results.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('Failed to load results:', e)
  }
}

onMounted(loadResults)
</script>

<style scoped>
.results-page {
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
  background: var(--bg-panel); /* Used bg-panel explicitly */
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

.results-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

.filters {
  display: flex;
  gap: var(--space-3);
}

.filter-select {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-panel); 
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: var(--space-3) var(--space-4);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.results-table th {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  background: rgba(255,255,255,0.02);
}

.results-table td {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.results-table tr.clickable {
  cursor: pointer;
  transition: background var(--transition-fast);
}

.results-table tr.clickable:hover {
  background: rgba(255,255,255,0.05);
}

.col-id {
  font-weight: var(--font-weight-medium);
  color: var(--color-blue);
}

.col-time {
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
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
