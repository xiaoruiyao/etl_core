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
        <AppCard :title="`结果列表（共 ${resultsTotal} 条）`">
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
              <div class="result-time">{{ formatTime(result.start_time) }}</div>
              <div class="result-arrow">→</div>
            </div>
          </div>
          <div class="pagination-bar">
            <button class="page-btn" :disabled="resultsPage <= 1" @click="goResultsPage(resultsPage - 1)">‹ 上一页</button>
            <span class="page-info">{{ resultsPage }} / {{ resultsTotalPages }}</span>
            <button class="page-btn" :disabled="resultsPage >= resultsTotalPages" @click="goResultsPage(resultsPage + 1)">下一页 ›</button>
          </div>
        </AppCard>
      </div>

      <!-- Alarms Tab -->
      <div v-show="activeTab === 'alarms'" class="tab-content">
        <AppCard :title="`报警记录（共 ${alarmsTotal} 条）`">
          <!-- 筛选栏 -->
          <div class="alarm-filters">
            <button
              class="filter-btn"
              :class="{ active: alarmHasParent === null }"
              @click="setAlarmFilter(null)"
            >全部</button>
            <button
              class="filter-btn filter-parent"
              :class="{ active: alarmHasParent === true }"
              @click="setAlarmFilter(true)"
            >↑ 有父级关联</button>
            <button
              class="filter-btn"
              :class="{ active: alarmHasParent === false }"
              @click="setAlarmFilter(false)"
            >根告警</button>
          </div>
          <div class="alarms-list" v-if="alarms.length > 0">
            <div v-for="alarm in alarms" :key="alarm.id" class="alarm-row">
              <AppBadge :type="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'" size="sm">
                {{ alarm.alarm_level }}
              </AppBadge>
              <span class="alarm-code">{{ alarm.alarm_code }}</span>
              <span class="alarm-msg">{{ alarm.alarm_msg }}</span>
              <span v-if="alarm.parent_alarm_id" class="alarm-parent-tag">↑ #{{ alarm.parent_alarm_id }}</span>
              <a class="alarm-link" @click.stop="goToResult(alarm.result_id)">#{{ alarm.result_id }}</a>
            </div>
          </div>
          <div v-else class="empty-state">暂无报警</div>
          <div class="pagination-bar">
            <button class="page-btn" :disabled="alarmsPage <= 1" @click="goAlarmsPage(alarmsPage - 1)">‹ 上一页</button>
            <span class="page-info">{{ alarmsPage }} / {{ alarmsTotalPages }}</span>
            <button class="page-btn" :disabled="alarmsPage >= alarmsTotalPages" @click="goAlarmsPage(alarmsPage + 1)">下一页 ›</button>
          </div>
        </AppCard>
      </div>
      
      <!-- Curves Tab - Combined Step Curves -->
      <div v-show="activeTab === 'curves'" class="tab-content">
        <!-- 结果导航 -->
        <div class="curve-nav" v-if="recentResults.length > 0">
          <button class="nav-btn" :disabled="currentResultIdx >= recentResults.length - 1" @click="switchResult(currentResultIdx + 1)">← 上一条</button>
          <span class="nav-info">
            结果 <strong>#{{ recentResults[currentResultIdx]?.id }}</strong>
            <span class="nav-status" :class="recentResults[currentResultIdx]?.result_status === 1 ? 'ok' : 'nok'">
              {{ recentResults[currentResultIdx]?.result_status === 1 ? 'OK' : 'NOK' }}
            </span>
            <span class="nav-time">{{ formatTime(recentResults[currentResultIdx]?.start_time) }}</span>
            <span class="nav-count">{{ currentResultIdx + 1 }} / {{ recentResults.length }}</span>
          </span>
          <button class="nav-btn" :disabled="currentResultIdx <= 0" @click="switchResult(currentResultIdx - 1)">下一条 →</button>
        </div>

        <!-- 关联告警面板 -->
        <div class="curve-alarms" v-if="curveAlarms.length > 0">
          <span class="alarms-title">⚠ 关联告警 ({{ curveAlarms.length }})</span>
          <div class="alarm-chips">
            <span
              v-for="alarm in curveAlarms"
              :key="alarm.id"
              class="alarm-chip"
              :class="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'"
            >
              <span class="chip-code">{{ alarm.alarm_code }}</span>
              <span class="chip-msg">{{ alarm.alarm_msg }}</span>
              <span v-if="alarm.parent_alarm_id" class="chip-parent">↑#{{ alarm.parent_alarm_id }}</span>
            </span>
          </div>
        </div>

        <AppCard title="曲线图">
          <div v-if="curvesLoading" class="empty-state">加载曲线中...</div>
          <div v-else-if="combinedCurves.length > 0" class="combined-chart">
            <CombinedCurveChart
              :curves="combinedCurves"
              :steps="latestSteps"
              :alarms="curveAlarms"
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
import { ref, computed, onMounted, watch } from 'vue'
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
const activeTab = ref('realtime')
const stats = ref({})

// Results 分页
const recentResults = ref([])
const resultsPage = ref(1)
const resultsPageSize = 10
const resultsTotal = ref(0)
const resultsTotalPages = computed(() => Math.max(1, Math.ceil(resultsTotal.value / resultsPageSize)))

// Alarms 分页 + 筛选
const alarms = ref([])
const alarmsPage = ref(1)
const alarmsPageSize = 20
const alarmsTotal = ref(0)
const alarmsTotalPages = computed(() => Math.max(1, Math.ceil(alarmsTotal.value / alarmsPageSize)))
const alarmHasParent = ref(null)  // null=全部, true=有父级, false=根告警

// Curves
const combinedCurves = ref([])
const latestSteps = ref([])
const curveAlarms = ref([])
const curvesLoaded = ref(false)
const curvesLoading = ref(false)
const currentResultIdx = ref(0)

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

const loadResults = async () => {
  const data = await getDeviceResults(deviceName, { page: resultsPage.value, page_size: resultsPageSize })
  recentResults.value = data.items || []
  resultsTotal.value = data.total || 0
}

const loadAlarms = async () => {
  const params = { page: alarmsPage.value, page_size: alarmsPageSize }
  if (alarmHasParent.value !== null) params.has_parent = alarmHasParent.value
  const data = await getDeviceAlarms(deviceName, params)
  alarms.value = data.items || []
  alarmsTotal.value = data.total || 0
}

const goResultsPage = async (page) => {
  resultsPage.value = page
  await loadResults()
}

const goAlarmsPage = async (page) => {
  alarmsPage.value = page
  await loadAlarms()
}

const setAlarmFilter = async (val) => {
  alarmHasParent.value = val
  alarmsPage.value = 1
  await loadAlarms()
}

onMounted(async () => {
  try {
    const [detail, , ] = await Promise.all([
      getDeviceDetail(deviceName),
      loadResults(),
      loadAlarms()
    ])
    stats.value = detail
  } catch (e) {
    console.error('Failed to load device detail:', e)
  } finally {
    loading.value = false
  }
})

const loadCurves = async () => {
  if (recentResults.value.length === 0) return
  const resultId = recentResults.value[currentResultIdx.value].id
  curvesLoading.value = true
  try {
    const [curvesResp, stepsData] = await Promise.all([
      getResultCurves(resultId),
      getResultSteps(resultId)
    ])
    combinedCurves.value = curvesResp.items || []
    curveAlarms.value = curvesResp.alarms || []
    latestSteps.value = stepsData || []
    curvesLoaded.value = true
  } catch (e) {
    console.error('Failed to load curves:', e)
  } finally {
    curvesLoading.value = false
  }
}

const switchResult = async (idx) => {
  currentResultIdx.value = idx
  curvesLoaded.value = false
  await loadCurves()
}

// 曲线懒加载：仅在切换到曲线 Tab 时才请求
watch(activeTab, async (tab) => {
  if (tab === 'curves' && !curvesLoaded.value) {
    await loadCurves()
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
.alarm-parent-tag { font-size: var(--font-size-xs); color: var(--color-warning); background: rgba(245,158,11,0.1); padding: 2px 6px; border-radius: var(--radius-full); white-space: nowrap; }
.alarm-link { color: var(--color-primary-light); cursor: pointer; }
.alarm-link:hover { text-decoration: underline; }

/* Alarm Filters */
.alarm-filters {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.filter-btn {
  padding: var(--space-2) var(--space-4);
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--font-size-xs);
  transition: all var(--transition-fast);
}
.filter-btn:hover { background: rgba(255,255,255,0.1); color: var(--text-primary); }
.filter-btn.active { background: var(--gradient-primary); border-color: transparent; color: white; }
.filter-btn.filter-parent.active { background: linear-gradient(135deg, #F59E0B, #EF4444); border-color: transparent; color: white; }

/* Pagination */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
  margin-top: var(--space-3);
}
.page-btn {
  padding: var(--space-2) var(--space-4);
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}
.page-btn:hover:not(:disabled) { background: rgba(255,255,255,0.1); color: var(--text-primary); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-info { font-size: var(--font-size-sm); color: var(--text-tertiary); min-width: 60px; text-align: center; }

/* Combined Chart */
.combined-chart {
  padding: var(--space-4);
}

/* Curve Navigation */
.curve-nav {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: var(--glass-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.nav-btn {
  padding: var(--space-2) var(--space-4);
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
}
.nav-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.12);
  color: var(--text-primary);
}
.nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.nav-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.nav-info strong { color: var(--text-primary); }
.nav-status { padding: 2px 8px; border-radius: var(--radius-full); font-size: var(--font-size-xs); font-weight: bold; }
.nav-status.ok { background: rgba(16,185,129,0.15); color: #10B981; }
.nav-status.nok { background: rgba(239,68,68,0.15); color: #EF4444; }
.nav-time { color: var(--text-tertiary); }
.nav-count { margin-left: auto; color: var(--text-tertiary); font-size: var(--font-size-xs); }

/* Curve Alarms Panel */
.curve-alarms {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: rgba(239,68,68,0.06);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: var(--radius-md);
}

.alarms-title {
  white-space: nowrap;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: #EF4444;
  padding-top: 2px;
}

.alarm-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.alarm-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 3px var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  border: 1px solid;
}
.alarm-chip.error { background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.3); color: #FCA5A5; }
.alarm-chip.warning { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.3); color: #FCD34D; }
.chip-code { font-weight: bold; }
.chip-msg { color: inherit; opacity: 0.8; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip-parent { opacity: 0.6; }

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
