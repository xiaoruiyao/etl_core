<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-overlay" @click.self="close">
      <div class="modal-content">
        <div class="modal-header">
          <div class="modal-title">
            <span>历史趋势</span>
            <span class="modal-subtitle" v-if="currentPoint">{{ currentPoint.name }}</span>
          </div>
          <button class="close-btn" @click="close">×</button>
        </div>
        
        <div class="modal-body">
          <div class="query-controls">
            <!-- Point Selector (Optional) -->
            <div class="point-selector" v-if="availablePoints.length > 0">
               <label>选择点位</label>
               <select v-model="currentPoint" class="point-select">
                 <option v-for="p in availablePoints" :key="p.uri" :value="p">
                   {{ p.name || p.uri }}
                 </option>
               </select>
            </div>
  
            <div class="time-picker">
              <label>开始时间</label>
              <input type="datetime-local" step="1" v-model="params.startTime">
            </div>
            <div class="time-picker">
              <label>结束时间</label>
              <input type="datetime-local" step="1" v-model="params.endTime">
            </div>
            <div class="quick-ranges">
              <button v-for="range in quickRanges" :key="range.label" @click="applyRange(range.minutes)" class="range-btn">
                {{ range.label }}
              </button>
            </div>
            <button class="query-btn" @click="queryHistory" :disabled="loading">
              {{ loading ? '查询中...' : '查询' }}
            </button>
          </div>
          
          <!-- Chart for numeric data -->
          <div class="history-chart-container" v-if="isNumeric">
            <canvas ref="canvasEl"></canvas>
            <div v-if="(!data || data.length === 0) && !loading" class="no-data">请选择点位并查询</div>
          </div>
          
          <!-- Table for non-numeric data -->
          <div class="history-table-container" v-else-if="data && data.length > 0">
            <table class="history-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>值</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in paginatedData" :key="idx">
                  <td>{{ formatTimestamp(row.t) }}</td>
                  <td>{{ row.v }}</td>
                </tr>
              </tbody>
            </table>
            <div class="table-pagination">
              <button @click="prevPage" :disabled="currentPage <= 1">上一页</button>
              <span>{{ currentPage }} / {{ totalPages }}</span>
              <button @click="nextPage" :disabled="currentPage >= totalPages">下一页</button>
            </div>
          </div>
          
          <div v-else-if="!loading" class="no-data-standalone">请选择点位并查询</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { getDeviceUris } from '../../api'

const props = defineProps({
  modelValue: Boolean,
  device: String, // Device Name/ID to fetch points list
  point: Object,  // Initial selected point { uri, name }
  startTime: [String, Date],
  endTime: [String, Date]
})

const emit = defineEmits(['update:modelValue'])

const formatInput = (d) => {
  if (!d) return ''
  const date = new Date(d)
  const pad = n => n < 10 ? '0' + n : n
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const quickRanges = [
  { label: '1小时', minutes: 60 },
  { label: '4小时', minutes: 240 },
  { label: '12小时', minutes: 720 },
  { label: '24小时', minutes: 1440 }
]

const applyRange = (minutes) => {
  const end = new Date()
  const start = new Date(end.getTime() - minutes * 60 * 1000)
  params.value.endTime = formatInput(end)
  params.value.startTime = formatInput(start)
}

const params = ref({ startTime: '', endTime: '' })
const loading = ref(false)
const data = ref(null)
const canvasEl = ref(null)

const availablePoints = ref([])
const currentPoint = ref(null)

const close = () => {
  emit('update:modelValue', false)
}

// Pagination for table
const pageSize = 20
const currentPage = ref(1)

const isNumeric = computed(() => {
  if (!data.value || data.value.length === 0) return true // Default to chart
  return data.value.every(d => !isNaN(Number(d.v)) && d.v !== null && d.v !== '')
})

const paginatedData = computed(() => {
  if (!data.value) return []
  const start = (currentPage.value - 1) * pageSize
  return data.value.slice(start, start + pageSize)
})

const totalPages = computed(() => {
  if (!data.value) return 1
  return Math.ceil(data.value.length / pageSize)
})

const prevPage = () => { if (currentPage.value > 1) currentPage.value-- }
const nextPage = () => { if (currentPage.value < totalPages.value) currentPage.value++ }

const formatTimestamp = (ts) => {
  const d = new Date(ts)
  const pad = n => n < 10 ? '0' + n : n
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// Fetch points if device is provided
const loadPoints = async () => {
  if (props.device) {
    try {
      const resp = await getDeviceUris(props.device)
      availablePoints.value = resp.items || []
      // If no point selected but we have points, select first
      if (!currentPoint.value && availablePoints.value.length > 0) {
        currentPoint.value = availablePoints.value[0]
      }
    } catch (e) {
      console.error("Failed to load points", e)
    }
  }
}

watch(() => props.modelValue, async (val) => {
  if (val) {
    // Init params
    let start = props.startTime
    let end = props.endTime
    
    // Default to last 1h if not provided
    if (!end) end = new Date()
    if (!start) start = new Date(new Date(end).getTime() - 60 * 60 * 1000)
    
    params.value.startTime = formatInput(start)
    params.value.endTime = formatInput(end)
    
    // Init point
    if (props.point) {
      currentPoint.value = props.point
    }
    
    // If device provided, allow switching (fetch list)
    if (props.device) {
      loadPoints()
    }
    
    data.value = null
    // If we have everything, auto query? No, wait for user interact or explicitly auto-query if needed. 
    // User requirement: "Default query basic info start/end time". Maybe auto query if point is set.
    if (currentPoint.value && props.startTime && props.endTime) {
       // We can auto query. Let's wait for user capability to change first as generally better UX, 
       // but user said "Default query...".
       // Let's just set the times.
    }
  }
})

// Watch point change to clear data?
watch(currentPoint, () => {
  // data.value = null
})

const queryHistory = async () => {
  if (!currentPoint.value) return
  
  loading.value = true
  data.value = null 
  
  try {
    const payload = {
      detail: {
        startTime: params.value.startTime.replace('T', ' '), 
        endTime: params.value.endTime.replace('T', ' '),
        maxSizePerNode: 1000,
        returnBounds: true
      },
      nodes: [
        { browsePath: currentPoint.value.uri }
      ]
    }
    
    console.log('Querying history:', payload)
    
    const response = await fetch('http://localhost:8000/api/proxy/timeseries/history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (response.ok) {
      const resData = await response.json()
      
      if (resData.code === '0x00000000' && Array.isArray(resData.result)) {
        let points = []
        
        // Format C (Wrapped in historyData)
        if (resData.result[0] && Array.isArray(resData.result[0].historyData)) {
            points = resData.result[0].historyData.map(p => ({ 
               t: p.t, 
               v: p.v // Keep raw value (string/number)
            }))
             console.log('Parsed history (Format C - historyData):', points.length)
        }
        // Format A
        else if (resData.result.length > 0 && resData.result[0].t !== undefined) {
             points = resData.result.map(p => ({ t: p.t, v: p.v }))
        } 
        // Format B (Packed)
        else if (resData.result[0] && resData.result[0].v && typeof resData.result[0].v === 'string' && resData.result[0].v.startsWith('[')) {
           try {
             const rawPoints = JSON.parse(resData.result[0].v)
             if (Array.isArray(rawPoints)) {
                points = rawPoints.map(p => {
                    if (Array.isArray(p) && p.length >= 2) return { t: p[0], v: p[1] }
                    if (typeof p === 'object') return { t: p.t, v: p.v }
                    return null
                })
             }
           } catch(e) { console.error("Parse error", e) }
        }
        
        data.value = points
        await nextTick()
        drawChart()
      }
    }
  } catch (e) {
    console.error("Query history failed", e)
  } finally {
    loading.value = false
  }
}

const drawChart = () => {
    if (!canvasEl.value || !data.value || data.value.length === 0) return
    const canvas = canvasEl.value
    const ctx = canvas.getContext('2d')
    const width = canvas.width = canvas.offsetWidth * 2
    const height = canvas.height = canvas.offsetHeight * 2
    
    ctx.clearRect(0, 0, width, height)
    
    const points = data.value
    const values = points.map(d => Number(d.v))
    
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const range = maxVal - minVal || 1
    
    // Padding for axis labels
    const paddingLeft = 80
    const paddingRight = 30
    const paddingTop = 30
    const paddingBottom = 60
    const chartW = width - paddingLeft - paddingRight
    const chartH = height - paddingTop - paddingBottom
    
    // Draw Y-axis labels (5 tick marks)
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = 'rgba(255,255,255,0.7)'
    ctx.font = '22px monospace'
    
    for (let i = 0; i <= 4; i++) {
      const val = minVal + (range * i / 4)
      const y = paddingTop + chartH - (i / 4) * chartH
      ctx.fillText(val.toFixed(2), paddingLeft - 10, y)
      // Grid line
      ctx.save()
      ctx.strokeStyle = 'rgba(255,255,255,0.1)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(paddingLeft, y)
      ctx.lineTo(paddingLeft + chartW, y)
      ctx.stroke()
      ctx.restore()
    }
    
    // Draw X-axis time labels (5-6 tick marks)
    const timestamps = points.map(d => new Date(d.t).getTime())
    const minTime = Math.min(...timestamps)
    const maxTime = Math.max(...timestamps)
    const timeRange = maxTime - minTime || 1
    
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.font = '20px monospace'
    
    const tickCount = 5
    for (let i = 0; i <= tickCount; i++) {
      const t = minTime + (timeRange * i / tickCount)
      const x = paddingLeft + (i / tickCount) * chartW
      const d = new Date(t)
      const pad = n => n < 10 ? '0' + n : n
      const label = `${pad(d.getHours())}:${pad(d.getMinutes())}`
      ctx.fillText(label, x, height - paddingBottom + 10)
      
      // Vertical grid line
      ctx.save()
      ctx.strokeStyle = 'rgba(255,255,255,0.05)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, paddingTop)
      ctx.lineTo(x, paddingTop + chartH)
      ctx.stroke()
      ctx.restore()
    }
    
    // Draw date range at bottom
    ctx.fillStyle = 'rgba(255,255,255,0.5)'
    ctx.font = '18px monospace'
    const startDate = new Date(minTime)
    const endDate = new Date(maxTime)
    const pad = n => n < 10 ? '0' + n : n
    const dateLabel = `${startDate.getMonth()+1}/${startDate.getDate()} - ${endDate.getMonth()+1}/${endDate.getDate()}`
    ctx.fillText(dateLabel, width / 2, height - 15)
    
    // Draw line chart
    ctx.beginPath()
    ctx.strokeStyle = '#00f3ff'
    ctx.lineWidth = 3
    ctx.lineJoin = 'round'
    
    points.forEach((p, i) => {
        const val = Number(p.v)
        const t = new Date(p.t).getTime()
        const x = paddingLeft + ((t - minTime) / timeRange) * chartW
        const y = paddingTop + chartH - ((val - minVal) / range) * chartH
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
    })
    ctx.stroke()
    
    // Gradient fill
    const grad = ctx.createLinearGradient(0, paddingTop, 0, paddingTop + chartH)
    grad.addColorStop(0, 'rgba(0, 243, 255, 0.3)')
    grad.addColorStop(1, 'rgba(0, 243, 255, 0)')
    
    // Close path for fill
    const lastT = new Date(points[points.length - 1].t).getTime()
    const firstT = new Date(points[0].t).getTime()
    ctx.lineTo(paddingLeft + ((lastT - minTime) / timeRange) * chartW, paddingTop + chartH)
    ctx.lineTo(paddingLeft + ((firstT - minTime) / timeRange) * chartW, paddingTop + chartH)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(5px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: rgba(13, 22, 35, 0.95);
  border: 1px solid var(--color-primary);
  box-shadow: 0 0 30px rgba(0, 243, 255, 0.2);
  width: 1100px;
  max-width: 95vw;
  max-height: 90vh;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  display: grid;
  grid-template-columns: auto 1fr 1fr auto;
  gap: 20px;
  align-items: end;
  margin-bottom: 20px;
  background: rgba(0, 0, 0, 0.2);
  padding: 15px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

@media (max-width: 900px) {
  .query-controls {
    grid-template-columns: 1fr 1fr;
  }
}

.point-selector, .time-picker {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.point-selector label, .time-picker label {
  font-size: 12px;
  color: var(--text-dim);
}

.point-selector select, .time-picker input {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(0, 243, 255, 0.3);
  color: white;
  padding: 10px 12px;
  border-radius: 4px;
  font-family: var(--font-mono);
  min-width: 220px;
  font-size: 14px;
}
.point-selector select option {
  background: #0d1623;
}
/* Interaction fix */
.point-selector select, .time-picker input {
  pointer-events: auto;
}

.quick-ranges {
  display: flex;
  gap: 10px;
  width: 100%;
  margin-top: 5px;
}

.range-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: var(--text-secondary);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.range-btn:hover {
  background: rgba(0, 243, 255, 0.2);
  color: white;
  border-color: var(--color-primary);
}

.query-btn {
  background: var(--color-primary);
  color: black;
  border: none;
  padding: 8px 20px;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
  height: 38px;
  min-width: 80px;
}
.query-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.history-chart-container {
  height: 450px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  position: relative;
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

.no-data-standalone {
  text-align: center;
  color: var(--text-dim);
  padding: 60px 0;
}

/* Table for non-numeric data */
.history-table-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.3);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 13px;
}

.history-table thead {
  position: sticky;
  top: 0;
  background: rgba(0, 50, 70, 0.95);
  z-index: 1;
}

.history-table th,
.history-table td {
  padding: 10px 15px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.history-table th {
  color: var(--color-primary);
  font-weight: normal;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
}

.history-table td {
  color: var(--text-secondary);
}

.history-table tbody tr:hover {
  background: rgba(0, 243, 255, 0.05);
}

.table-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 12px;
  background: rgba(0, 30, 50, 0.8);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.table-pagination button {
  background: rgba(0, 243, 255, 0.2);
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.table-pagination button:hover:not(:disabled) {
  background: var(--color-primary);
  color: black;
}

.table-pagination button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.table-pagination span {
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
