<template>
  <div class="result-detail">
    <AppHeader :title="`结果 #${resultId}`" :subtitle="result?.device_name">
      <AppButton variant="secondary" @click="$router.back()">← 返回</AppButton>
    </AppHeader>
    
    <div class="detail-content" v-if="result">
      <!-- Basic Info -->
      <div class="info-grid">
        <AppCard title="基本信息">
          <div class="info-list">
            <div class="info-item">
              <span class="info-label">设备</span>
              <span class="info-value">{{ result.device_name }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">BSN</span>
              <span class="info-value">{{ result.bsn || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">工艺</span>
              <span class="info-value">{{ result.craft_type }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">程序</span>
              <span class="info-value">{{ result.program_id }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">状态</span>
              <AppBadge :type="getStatusType(result.result_status)">
                {{ getStatusText(result.result_status) }}
              </AppBadge>
            </div>
            <div class="info-item">
              <span class="info-label">周期时间</span>
              <span class="info-value">{{ result.cycle_time?.toFixed(3) }}s</span>
            </div>
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span class="info-value">{{ formatTime(result.start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span class="info-value">{{ formatTime(result.end_time) }}</span>
            </div>
          </div>
        </AppCard>
        
        <AppCard title="关键指标">
          <div class="key-value-display">
            <div class="kv-main">{{ result.key_value?.toFixed(2) || '-' }}</div>
            <div class="kv-label">关键值</div>
          </div>
        </AppCard>
      </div>
      
      <!-- Alarms -->
      <AppCard title="报警信息" v-if="alarms.length > 0">
        <template #header>
           <div style="flex:1"></div>
           <AppButton size="sm" variant="outline" @click="openHistoryAnalysis">
             关联点位分析
           </AppButton>
        </template>
        <div class="alarms-list">
          <div v-for="alarm in alarms" :key="alarm.id" class="alarm-item">
            <div class="alarm-content">
              <div class="alarm-header">
                <AppBadge :type="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'" size="sm">
                  {{ alarm.alarm_level }}
                </AppBadge>
                <div class="alarm-title-group">
                  <span class="alarm-code">{{ alarm.alarm_code }}</span>
                  <span class="alarm-msg">{{ alarm.alarm_msg }}</span>
                </div>
              </div>
              
              <!-- Hierarchy Chain -->
              <div class="alarm-hierarchy" v-if="alarm.hierarchy && alarm.hierarchy.length > 1">
                <div class="hierarchy-label">溯源分析:</div>
                <div class="hierarchy-chain">
                  <template v-for="(node, idx) in alarm.hierarchy" :key="node.id">
                    <div 
                      class="hierarchy-node"
                      :class="{ 
                        'is-root': idx === 0,
                        'is-current': node.id === alarm.id 
                      }"
                    >
                      <span class="node-code">{{ node.alarm_code }}</span>
                    </div>
                    <div class="node-separator" v-if="idx < alarm.hierarchy.length - 1"></div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </AppCard>

      <!-- Steps -->
      <AppCard title="步骤流程" v-if="steps.length > 0">
        <div class="steps-flow">
          <div 
            v-for="(step, index) in steps" 
            :key="step.id"
            class="step-item"
            :class="{ 'step-ok': step.step_result === 1, 'step-nok': step.step_result === 0 }"
          >
            <div class="step-index">{{ step.step_index }}</div>
            <div class="step-info">
              <div class="step-name">{{ step.step_name || `Step ${step.step_index}` }}</div>
              <div class="step-value">值: {{ step.step_value?.toFixed(2) || '-' }}</div>
            </div>
            <AppBadge :type="step.step_result === 1 ? 'success' : 'error'" size="sm">
              {{ step.step_result === 1 ? 'OK' : 'NOK' }}
            </AppBadge>
            <div v-if="index < steps.length - 1" class="step-arrow">→</div>
          </div>
        </div>
      </AppCard>
      
      <!-- Curves -->
      <AppCard title="曲线数据" v-if="groupedCurves.length > 0">
        <div class="curves-container">
          <div v-for="group in groupedCurves" :key="group.step" class="curve-group">
            <h4 class="curve-step-title">Step {{ group.step }}</h4>
            <div class="curves-grid">
              <div v-for="curve in group.curves" :key="curve.id" class="curve-item">
                <CurveChart
                  :title="curve.curve_type"
                  :curves="[{
                    name: curve.curve_type,
                    x: curve.data_points?.x || [],
                    y: curve.data_points?.y || [],
                    color: getCurveColor(curve.curve_type),
                    showArea: true
                  }]"
                  :xAxisLabel="getXAxisLabel(curve.curve_type)"
                  :yAxisLabel="curve.curve_type"
                  height="220px"
                />
              </div>
            </div>
          </div>
        </div>
      </AppCard>
      

    </div>
    
    <div v-else class="loading">加载中...</div>

    <!-- History Dialog -->
    <HistoryDialog 
      v-model="showHistoryDialog"
      :device="result?.device_name"
      :startTime="historyStartTime"
      :endTime="historyEndTime"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/layout/AppHeader.vue'
import AppCard from '../components/common/AppCard.vue'
import AppBadge from '../components/common/AppBadge.vue'
import AppButton from '../components/common/AppButton.vue'
import CurveChart from '../components/charts/CurveChart.vue'
import HistoryDialog from '../components/common/HistoryDialog.vue'
import { getResultDetail, getResultCurves, getResultSteps, getAlarms, getAlarmHierarchy } from '../api'

const route = useRoute()
const resultId = route.params.id

const result = ref(null)
const steps = ref([])
const curves = ref([])
const alarms = ref([])

// History Dialog
const showHistoryDialog = ref(false)
const historyStartTime = ref('')
const historyEndTime = ref('')

const openHistoryAnalysis = () => {
  if (result.value) {
    historyStartTime.value = result.value.start_time
    historyEndTime.value = result.value.end_time
    showHistoryDialog.value = true
  }
}

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

const getCurveColor = (type) => {
  const colors = {
    'TORQUE': '#007AFF',
    'ANGLE': '#34C759',
    'DEPTH': '#FF9500',
    'SPEED': '#AF52DE',
    'PRESSURE': '#FF3B30',
    'FORCE': '#007AFF',
    'STROKE': '#5AC8FA'
  }
  return colors[type] || '#007AFF'
}

const getXAxisLabel = (type) => {
  if (type === 'TORQUE_ANGLE') return 'Angle (deg)'
  return 'Time (s)'
}

const groupedCurves = computed(() => {
  const groups = {}
  curves.value.forEach(c => {
    const step = c.step ?? 0
    if (!groups[step]) groups[step] = []
    groups[step].push(c)
  })
  return Object.entries(groups)
    .map(([step, curves]) => ({ step: parseInt(step), curves }))
    .sort((a, b) => a.step - b.step)
})

onMounted(async () => {
  try {
    result.value = await getResultDetail(resultId)
  } catch (e) {
    console.error('Failed to load result:', e)
  }
  
  try {
    const data = await getResultSteps(resultId)
    steps.value = data || []
  } catch (e) {
    console.error('Failed to load steps:', e)
  }
  
  try {
    const data = await getResultCurves(resultId)
    curves.value = data || []
  } catch (e) {
    console.error('Failed to load curves:', e)
  }
  
  try {
    const data = await getAlarms({ result_id: resultId })
    const alarmsData = data.items || []
    
    // Fetch hierarchy for each alarm
    alarms.value = await Promise.all(alarmsData.map(async (alarm) => {
      try {
        const hierarchy = await getAlarmHierarchy(alarm.id)
        return { ...alarm, hierarchy }
      } catch (e) {
        console.error(`Failed to load hierarchy for alarm ${alarm.id}:`, e)
        return alarm
      }
    }))
  } catch (e) {
    console.error('Failed to load alarms:', e)
  }
})
</script>

<style scoped>
.result-detail {
  min-height: 100vh;
}

.detail-content {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.info-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-5);
}

.info-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.info-value {
  font-size: var(--font-size-md);
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
}

.key-value-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
}

.kv-main {
  font-size: 48px;
  font-weight: var(--font-weight-bold);
  color: var(--color-blue);
}

.kv-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-top: var(--space-2);
}

.steps-flow {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  overflow-x: auto;
  padding: var(--space-4) 0;
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-grey-3);
}

.step-item.step-ok { border-left-color: var(--color-success); }
.step-item.step-nok { border-left-color: var(--color-error); }

.step-index {
  width: 28px;
  height: 28px;
  background: var(--bg-primary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
}

.step-info {
  display: flex;
  flex-direction: column;
}

.step-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.step-value {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.step-arrow {
  color: var(--text-tertiary);
  font-size: 20px;
}

.curves-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.curve-step-title {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-4);
  color: var(--text-secondary);
}

.curves-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.curve-item {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
}

.alarms-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.alarm-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  background: rgba(255, 59, 48, 0.05);
  border-radius: var(--radius-sm);
}

.alarm-code {
  font-weight: var(--font-weight-medium);
  min-width: 80px;
}

.alarm-msg {
  flex: 1;
  flex: 1;
  color: var(--text-secondary);
}

.alarm-title-group {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex: 1;
}

.alarm-hierarchy {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-sm);
  margin-top: var(--space-2);
  width: fit-content;
}

.hierarchy-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  color: var(--text-secondary);
  margin-right: var(--space-2);
}

.hierarchy-chain {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.hierarchy-node {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: 12px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.hierarchy-node .node-code {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

/* Root Node Style */
.hierarchy-node.is-root {
  background: rgba(255, 59, 48, 0.15);
  border-color: rgba(255, 59, 48, 0.3);
}
.hierarchy-node.is-root .node-code {
  color: var(--color-error);
  font-weight: var(--font-weight-bold);
}

/* Current Node Style */
.hierarchy-node.is-current {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--text-secondary);
}
.hierarchy-node.is-current .node-code {
  color: var(--text-primary);
}

.node-separator {
  width: 12px;
  height: 2px;
  background: var(--bg-tertiary);
  border-radius: 1px;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 50vh;
  color: var(--text-secondary);
}
</style>
