<template>
  <div class="device-detail">
    <AppHeader :title="deviceName" subtitle="设备详情">
      <AppButton variant="secondary" @click="$router.back()">← 返回</AppButton>
    </AppHeader>
    
    <div class="detail-content" v-if="!loading">
      <!-- Device Summary -->
      <div class="summary-section">
        <div class="summary-cards">
          <div class="summary-card total">
            <div class="summary-icon">📊</div>
            <div class="summary-info">
              <span class="summary-value">{{ stats.total || 0 }}</span>
              <span class="summary-label">总结果</span>
            </div>
          </div>
          <div class="summary-card ok">
            <div class="summary-icon">✅</div>
            <div class="summary-info">
              <span class="summary-value">{{ stats.ok_rate?.toFixed(1) || 0 }}%</span>
              <span class="summary-label">合格率</span>
            </div>
            <div class="summary-bar">
              <div class="bar-fill" :style="{ width: (stats.ok_rate || 0) + '%' }"></div>
            </div>
          </div>
          <div class="summary-card nok">
            <div class="summary-icon">❌</div>
            <div class="summary-info">
              <span class="summary-value">{{ stats.nok_count || 0 }}</span>
              <span class="summary-label">NOK 数量</span>
            </div>
          </div>
          <div class="summary-card alarm">
            <div class="summary-icon">🔔</div>
            <div class="summary-info">
              <span class="summary-value">{{ stats.alarm_count || 0 }}</span>
              <span class="summary-label">报警数</span>
            </div>
          </div>
          <div class="summary-card uri" v-if="stats.uri_count > 0">
            <div class="summary-icon">📡</div>
            <div class="summary-info">
              <span class="summary-value">{{ stats.uri_count || 0 }}</span>
              <span class="summary-label">实时点位</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Quick View Tabs -->
      <div class="view-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.key"
          class="view-tab"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.icon }} {{ tab.label }}
          <span v-if="tab.key === 'realtime' && stats.uri_count > 0" class="tab-badge">
            {{ stats.uri_count }}
          </span>
        </button>
      </div>
      
      <!-- Realtime Data Tab -->
      <div v-show="activeTab === 'realtime'" class="tab-content">
        <RealtimePanel :deviceId="deviceName" />
      </div>
      
      <!-- Results Tab -->
      <div v-show="activeTab === 'results'" class="tab-content">
        <AppCard title="最近结果">
          <div class="results-list">
            <div 
              v-for="result in recentResults" 
              :key="result.id"
              class="result-row"
              @click="goToResult(result.id)"
            >
              <div class="result-status">
                <AppBadge :type="result.result_status === 1 ? 'success' : 'error'" size="sm" showDot>
                  {{ result.result_status === 1 ? 'OK' : 'NOK' }}
                </AppBadge>
              </div>
              <div class="result-info">
                <span class="result-id">#{{ result.id }}</span>
                <span class="result-bsn">{{ result.bsn || '-' }}</span>
              </div>
              <div class="result-value">
                {{ result.key_value?.toFixed(2) || '-' }}
              </div>
              <div class="result-time">
                {{ formatTime(result.start_time) }}
              </div>
              <div class="result-arrow">→</div>
            </div>
          </div>
        </AppCard>
      </div>
      
      <!-- Alarms Tab -->
      <div v-show="activeTab === 'alarms'" class="tab-content">
        <AppCard title="报警记录">
          <div class="alarms-list" v-if="alarms.length > 0">
            <div v-for="alarm in alarms" :key="alarm.id" class="alarm-row">
              <AppBadge :type="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'" size="sm">
                {{ alarm.alarm_level }}
              </AppBadge>
              <span class="alarm-code">{{ alarm.alarm_code }}</span>
              <span class="alarm-msg">{{ alarm.alarm_msg }}</span>
              <a class="alarm-link" @click="goToResult(alarm.result_id)">#{{ alarm.result_id }}</a>
            </div>
          </div>
          <div v-else class="empty-state">暂无报警</div>
        </AppCard>
      </div>
      
      <!-- Curves Tab - Combined Step Curves -->
      <div v-show="activeTab === 'curves'" class="tab-content">
        <AppCard title="最新结果曲线 (合并展示)">
          <div v-if="combinedCurves.length > 0" class="combined-chart">
            <CombinedCurveChart 
              :curves="combinedCurves"
              :steps="latestSteps"
              height="450px"
            />
          </div>
          <div v-else class="empty-state">暂无曲线数据</div>
        </AppCard>
      </div>
    </div>
    
    <div v-else class="loading-state">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/layout/AppHeader.vue'
import AppCard from '../components/common/AppCard.vue'
import AppBadge from '../components/common/AppBadge.vue'
import AppButton from '../components/common/AppButton.vue'
import CombinedCurveChart from '../components/charts/CombinedCurveChart.vue'
import RealtimePanel from '../components/realtime/RealtimePanel.vue'
import { getDeviceDetail, getDeviceResults, getDeviceAlarms, getResultCurves, getResultSteps } from '../api'

const route = useRoute()
const router = useRouter()
const deviceName = decodeURIComponent(route.params.name)

const loading = ref(true)
const activeTab = ref('realtime')  // Default to realtime tab
const stats = ref({})
const recentResults = ref([])
const alarms = ref([])
const combinedCurves = ref([])
const latestSteps = ref([])

const tabs = computed(() => {
  const baseTabs = [
    { key: 'realtime', label: '实时数据', icon: '📡' },
    { key: 'results', label: '结果', icon: '📋' },
    { key: 'alarms', label: '报警', icon: '🔔' },
    { key: 'curves', label: '曲线', icon: '📈' }
  ]
  return baseTabs
})

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

const goToResult = (id) => {
  router.push(`/results/${id}`)
}

onMounted(async () => {
  try {
    // Load device stats
    const detail = await getDeviceDetail(deviceName)
    stats.value = detail
    
    // Load recent results
    const results = await getDeviceResults(deviceName, { limit: 10 })
    recentResults.value = results.items || []
    
    // Load alarms
    const alarmsData = await getDeviceAlarms(deviceName, { limit: 20 })
    alarms.value = alarmsData.items || []
    
    // Load curves for latest result
    if (recentResults.value.length > 0) {
      const latestId = recentResults.value[0].id
      const curvesData = await getResultCurves(latestId)
      combinedCurves.value = curvesData || []
      
      const stepsData = await getResultSteps(latestId)
      latestSteps.value = stepsData || []
    }
  } catch (e) {
    console.error('Failed to load device detail:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.device-detail {
  min-height: 100vh;
}

.detail-content {
  padding: var(--space-6) var(--space-8);
}

/* Summary Section */
.summary-section {
  margin-bottom: var(--space-6);
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-5);
}

.summary-card {
  position: relative;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.summary-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.summary-card.total::before { background: var(--gradient-primary); }
.summary-card.ok::before { background: var(--color-success); }
.summary-card.nok::before { background: var(--color-error); }
.summary-card.alarm::before { background: var(--color-warning); }
.summary-card.uri::before { background: linear-gradient(135deg, #06B6D4, #3B82F6); }

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.summary-icon {
  font-size: 32px;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
}

.summary-info {
  flex: 1;
}

.summary-value {
  display: block;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.summary-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
}

.bar-fill {
  height: 100%;
  background: var(--color-success);
  transition: width 1s ease;
}

/* View Tabs */
.view-tabs {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  padding: var(--space-1);
  background: var(--glass-bg);
  border-radius: var(--radius-lg);
  width: fit-content;
}

.view-tab {
  position: relative;
  padding: var(--space-3) var(--space-5);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.view-tab:hover {
  color: var(--text-primary);
}

.view-tab.active {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--glow-primary);
}

.tab-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
}

.view-tab.active .tab-badge {
  background: rgba(255, 255, 255, 0.3);
}

/* Results List */
.results-list {
  display: flex;
  flex-direction: column;
}

.result-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.result-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.result-row:last-child {
  border-bottom: none;
}

.result-status { min-width: 80px; }
.result-info { flex: 1; display: flex; gap: var(--space-4); }
.result-id { color: var(--color-primary-light); font-weight: var(--font-weight-medium); }
.result-bsn { color: var(--text-secondary); }
.result-value { color: var(--text-primary); font-weight: var(--font-weight-medium); min-width: 80px; }
.result-time { color: var(--text-tertiary); font-size: var(--font-size-sm); }
.result-arrow { color: var(--text-tertiary); transition: all var(--transition-fast); }
.result-row:hover .result-arrow { color: var(--color-primary-light); transform: translateX(4px); }

/* Alarms List */
.alarms-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.alarm-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  background: rgba(239, 68, 68, 0.05);
  border-radius: var(--radius-sm);
}

.alarm-code { font-weight: var(--font-weight-medium); min-width: 80px; }
.alarm-msg { flex: 1; color: var(--text-secondary); }
.alarm-link { color: var(--color-primary-light); cursor: pointer; }
.alarm-link:hover { text-decoration: underline; }

/* Combined Chart */
.combined-chart {
  padding: var(--space-4);
}

/* Loading & Empty States */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
  gap: var(--space-4);
  color: var(--text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-secondary);
}
</style>
