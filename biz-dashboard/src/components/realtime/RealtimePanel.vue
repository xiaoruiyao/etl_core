<template>
  <div class="realtime-panel">
    <div class="panel-header">
      <div class="header-left">
        <span class="live-dot" :class="{ connected: isConnected }"></span>
        <span class="title">实时数据</span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div class="header-right">
        <span class="update-time" v-if="lastUpdate">{{ formatTime(lastUpdate) }}</span>
      </div>
    </div>
    
    <div class="uri-grid" v-if="uriData.length > 0">
      <transition-group name="uri">
        <div 
          v-for="item in uriData" 
          :key="item.uri"
          class="uri-card"
          :class="{ updated: item.justUpdated, 'chart-card': item.displayType === 'chart' }"
          @click="openHistory(item)"
        >
          <div class="uri-name">{{ item.name || '未命名' }}</div>
          
          <!-- Card 类型：显示当前值 -->
          <template v-if="item.displayType === 'card'">
            <div class="uri-value" :title="item.value">
              <span class="value-text">{{ formatValue(item.value) }}</span>
            </div>
          </template>
          
          <!-- Chart 类型：显示曲线图 -->
          <template v-else-if="item.displayType === 'chart'">
            <div class="chart-container">
              <canvas :ref="el => setChartRef(item.uri, el)" class="mini-chart"></canvas>
            </div>
            <div class="chart-value">
              <span class="current-value">{{ formatValue(item.value) }}</span>
            </div>
          </template>
          
          <div class="uri-meta">
            <span class="uri-timestamp" v-if="item.timestamp">
              {{ formatTimestamp(item.timestamp) }}
            </span>
          </div>
        </div>
      </transition-group>
    </div>
    
    <div v-else-if="isConnected" class="empty-state">
      <span class="loading-spinner"></span>
      <span>等待数据...</span>
    </div>
    
    <div v-else class="empty-state">
      <span class="offline-icon">📡</span>
      <span>未连接</span>
    </div>

    <!-- History Dialog -->
    <HistoryDialog 
      v-model="showHistoryModal"
      :point="selectedPoint"
      :startTime="historyParams.startTime"
      :endTime="historyParams.endTime"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import HistoryDialog from '../common/HistoryDialog.vue'
import { getDeviceUris } from '../../api'

const TIMESERIES_API_URL = 'https://bff-model-product-infra-system.iot-2f.seres.cn/bff/aggquery/v2/query/v2/queryCurrentRawValueByUri'

const props = defineProps({
  deviceId: {
    type: String,
    required: true
  }
})

const isConnected = ref(false)
const uriData = ref([])
const lastUpdate = ref(null)
let fetchInterval = null

// History Modal Logic
const showHistoryModal = ref(false)
const selectedPoint = ref(null)
const historyParams = ref({ startTime: '', endTime: '' })

const openHistory = (item) => {
  selectedPoint.value = item
  showHistoryModal.value = true
  
  // Default to last 1 hour
  const end = new Date()
  const start = new Date(end.getTime() - 60 * 60 * 1000)
  
  // Format for datetime-local input (YYYY-MM-DDThh:mm:ss)
  const formatInput = (d) => {
    const pad = n => n < 10 ? '0' + n : n
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  }
  
  historyParams.value = {
    startTime: formatInput(start),
    endTime: formatInput(end)
  }
}

// Chart 相关
const chartRefs = ref({})

const setChartRef = (uri, el) => {
  if (el) {
    chartRefs.value[uri] = el
  }
}

// 绘制迷你折线图
const drawChart = (canvas, history) => {
  if (!canvas || !history || history.length < 2) return
  
  const ctx = canvas.getContext('2d')
  const width = canvas.width = canvas.offsetWidth * 2  // 高清
  const height = canvas.height = canvas.offsetHeight * 2
  
  ctx.clearRect(0, 0, width, height)
  
  // 计算数据范围
  const values = history.map(h => h.v)
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const range = maxVal - minVal || 1
  
  // 边距
  const padding = 8
  const chartWidth = width - padding * 2
  const chartHeight = height - padding * 2
  
  // 绘制折线
  ctx.beginPath()
  ctx.strokeStyle = '#00f3ff'
  ctx.lineWidth = 2
  ctx.shadowBlur = 5
  ctx.shadowColor = '#00f3ff'
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'
  
  history.forEach((point, i) => {
    const x = padding + (i / (history.length - 1)) * chartWidth
    const y = padding + (1 - (point.v - minVal) / range) * chartHeight
    
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  })
  
  ctx.stroke()
  
  // 绘制渐变填充
  const gradient = ctx.createLinearGradient(0, padding, 0, height)
  gradient.addColorStop(0, 'rgba(0, 243, 255, 0.2)')
  gradient.addColorStop(1, 'rgba(0, 243, 255, 0)')
  
  ctx.lineTo(padding + chartWidth, height)
  ctx.lineTo(padding, height)
  ctx.closePath()
  ctx.fillStyle = gradient
  ctx.fill()
}

// 更新所有图表
const updateCharts = () => {
  uriData.value.forEach(item => {
    if (item.displayType === 'chart' && item.history.length >= 2) {
      const canvas = chartRefs.value[item.uri]
      if (canvas) {
        drawChart(canvas, item.history)
      }
    }
  })
}

const statusText = computed(() => {
  if (isConnected.value) return '已连接'
  return '加载中...'
})

const formatTime = (date) => {
  return date.toLocaleTimeString('zh-CN')
}

const formatTimestamp = (ts) => {
  return new Date(ts).toLocaleTimeString('zh-CN')
}

// 格式化数值，处理超长数组数据
const formatValue = (value) => {
  if (!value) return '-'
  
  // 检查是否是数组格式 [...]
  if (value.startsWith('[') && value.endsWith(']')) {
    try {
      const arr = JSON.parse(value)
      if (Array.isArray(arr) && arr.length > 0) {
        // 如果是数字数组，格式化显示
        if (typeof arr[0] === 'number') {
          // 显示前2个元素的简短形式
          const formatted = arr.slice(0, 2).map(n => 
            typeof n === 'number' ? n.toFixed(2) : n
          ).join(', ')
          return arr.length > 2 ? `[${formatted}, ...+${arr.length - 2}]` : `[${formatted}]`
        }
      }
    } catch (e) {
      // 解析失败，截断显示
    }
  }
  
  // 普通字符串，截断到合理长度
  if (value.length > 20) {
    return value.substring(0, 17) + '...'
  }
  
  return value
}

const fetchUriValues = async () => {
  if (uriData.value.length === 0) return
  
  try {
    const uris = uriData.value.map(u => u.uri)
    
    // 使用后端代理调用外部 API（解决 CORS）
    const response = await fetch('http://localhost:8000/api/proxy/timeseries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(uris)
    })
    
    if (response.ok) {
      const data = await response.json()
      console.log('Proxy response:', data)
      
      if (data.code === '0x00000000' && Array.isArray(data.result)) {
        lastUpdate.value = new Date()
        
        data.result.forEach((result, index) => {
          if (index < uriData.value.length) {
            const existing = uriData.value[index]
            // v 可能是字符串或数字，统一转换为字符串
            const rawValue = result.v !== null && result.v !== undefined ? String(result.v).trim() : null
            const newValue = rawValue
            const hasChanged = existing.value !== newValue
            
            existing.value = newValue
            existing.timestamp = result.t
            existing.status = result.s
            existing.justUpdated = hasChanged
            
            // 对于 chart 类型，追加历史数据
            if (existing.displayType === 'chart' && result.t && rawValue !== null) {
              // 尝试解析为数字
              const numValue = parseFloat(rawValue)
              if (!isNaN(numValue)) {
                existing.history.push({ t: result.t, v: numValue })
                // 保留最近 60 个点（约 3 分钟数据）
                if (existing.history.length > 60) {
                  existing.history.shift()
                }
              }
            }
            
            if (hasChanged) {
              setTimeout(() => {
                existing.justUpdated = false
              }, 500)
            }
          }
        })
        
        // 更新图表
        updateCharts()
      } else if (data.code && data.code !== '0x00000000') {
        console.error('API error:', data.code, data.msg)
      }
    }
  } catch (error) {
    console.error('Failed to fetch URI values:', error)
  }
}

const loadUriList = async () => {
  try {
    const data = await getDeviceUris(props.deviceId)
    if (data.items && data.items.length > 0) {
      uriData.value = data.items.map(item => ({
        id: item.id,
        uri: item.uri,
        name: item.name || '未命名',
        level: item.level,
        displayType: item.display_type || 'card',  // 新增：展示类型
        value: null,
        timestamp: null,
        status: null,
        justUpdated: false,
        history: []  // 新增：chart类型的历史数据
      }))
      
      isConnected.value = true
      
      // Fetch initial values
      await fetchUriValues()
      
      // Start polling every 3 seconds
      fetchInterval = setInterval(fetchUriValues, 3000)
    } else {
      console.log('No URIs found for device:', props.deviceId)
    }
  } catch (error) {
    console.error('Failed to load URI list:', error)
  }
}

onMounted(() => {
  if (props.deviceId) {
    loadUriList()
  }
})

onUnmounted(() => {
  if (fetchInterval) {
    clearInterval(fetchInterval)
  }
})

watch(() => props.deviceId, (newId) => {
  if (fetchInterval) {
    clearInterval(fetchInterval)
  }
  uriData.value = []
  isConnected.value = false
  
  if (newId) {
    loadUriList()
  }
})
</script>

<style scoped>
.realtime-panel {
  background: var(--bg-panel);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 243, 255, 0.1);
  border-radius: 0;
  overflow: hidden;
  clip-path: polygon(
    20px 0, 100% 0, 
    100% calc(100% - 20px), calc(100% - 20px) 100%, 
    0 100%, 0 20px
  );
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 25px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.2);
  background: linear-gradient(90deg, rgba(0, 243, 255, 0.05) 0%, transparent 100%);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-dot {
  width: 8px;
  height: 8px;
  background: var(--color-error);
  box-shadow: 0 0 10px var(--color-error);
  transform: rotate(45deg);
}

.live-dot.connected {
  background: var(--color-ok);
  box-shadow: 0 0 10px var(--color-ok);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: rotate(45deg) scale(1); }
  50% { opacity: 0.5; transform: rotate(45deg) scale(0.8); }
}

.title {
  font-family: var(--font-heading);
  font-size: 16px;
  color: var(--color-primary);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.status-text {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
}

.update-time {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-primary);
  text-shadow: 0 0 5px rgba(0, 243, 255, 0.3);
}

.uri-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
  padding: 20px;
}

.uri-card {
  position: relative;
  background: rgba(13, 22, 35, 0.4);
  border: 1px solid rgba(0, 243, 255, 0.1);
  padding: 15px;
  transition: all 0.3s ease;
}

.uri-card:hover {
  background: rgba(13, 22, 35, 0.8);
  border-color: var(--color-primary);
  box-shadow: inset 0 0 20px rgba(0, 243, 255, 0.1);
  transform: translateY(-2px);
}

.uri-card::before {
  content: '';
  position: absolute;
  top: -1px; left: -1px;
  width: 10px; height: 10px;
  border-top: 2px solid var(--color-primary);
  border-left: 2px solid var(--color-primary);
  opacity: 0.5;
}

.uri-card::after {
  content: '';
  position: absolute;
  bottom: -1px; right: -1px;
  width: 10px; height: 10px;
  border-bottom: 2px solid var(--color-primary);
  border-right: 2px solid var(--color-primary);
  opacity: 0.5;
}

.uri-card.updated {
  animation: highlight 0.5s ease-out;
}

@keyframes highlight {
  0% {
    background: rgba(0, 243, 255, 0.2);
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.5);
  }
  100% {
    background: rgba(13, 22, 35, 0.4);
    box-shadow: none;
  }
}

.uri-name {
  font-family: var(--font-heading);
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.value-text {
  font-family: var(--font-mono);
  font-size: 24px;
  color: var(--text-main);
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
}

.uri-timestamp {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-primary-dim);
}

/* Loading & Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px;
  color: var(--text-dim);
  font-family: var(--font-heading);
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 2px solid rgba(0, 243, 255, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Chart 类型卡片样式 */
.uri-card.chart-card {
  min-width: 250px;
  grid-column: span 2;
  border: 1px solid var(--color-primary-dim);
  background: radial-gradient(circle at center, rgba(0, 243, 255, 0.02) 0%, transparent 70%);
}

.chart-container {
  height: 80px;
  margin-bottom: 5px;
  border: 1px solid rgba(0, 243, 255, 0.1);
  background: rgba(0, 0, 0, 0.3);
  position: relative;
}

/* Grid overlay for chart */
.chart-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 243, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 243, 255, 0.1) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}

.mini-chart {
  width: 100%;
  height: 100%;
}

.chart-value {
  text-align: right;
}

.current-value {
  font-family: var(--font-mono);
  font-size: 18px;
  color: var(--color-primary);
  text-shadow: 0 0 8px var(--color-primary);
}

/* History Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: rgba(13, 22, 35, 0.95);
  border: 1px solid var(--color-primary);
  box-shadow: 0 0 30px rgba(0, 243, 255, 0.2);
  width: 800px;
  max-width: 90vw;
  border-radius: 8px;
  overflow: hidden;
}

.modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(90deg, rgba(0, 243, 255, 0.1), transparent);
}

.modal-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-primary);
  font-family: var(--font-heading);
}

.modal-subtitle {
  font-size: 0.8em;
  color: var(--text-dim);
  font-family: var(--font-mono);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 24px;
  cursor: pointer;
}
.close-btn:hover { color: white; }

.modal-body {
  padding: 20px;
}

.query-controls {
  display: flex;
  gap: 20px;
  align-items: flex-end;
  margin-bottom: 20px;
}

.time-picker {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.time-picker label {
  font-size: 12px;
  color: var(--text-dim);
}

.time-picker input {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 243, 255, 0.3);
  color: white;
  padding: 8px;
  border-radius: 4px;
  font-family: var(--font-mono);
  /* Fix input interaction */
  pointer-events: auto;
}

.query-btn {
  background: var(--color-primary);
  color: black;
  border: none;
  padding: 8px 20px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  height: 36px;
  min-width: 80px;
}
.query-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.history-chart-container {
  height: 300px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  margin-top: 10px;
}

canvas {
  width: 100%;
  height: 100%;
}

.no-data {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-dim);
}
</style>
