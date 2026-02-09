<template>
  <div class="dashboard">
    <AppHeader title="仪表盘" subtitle="设备工艺数据概览">
      <div class="live-indicator">
        <span class="live-dot"></span>
        <span class="live-text">实时数据</span>
      </div>
    </AppHeader>
    
    <div class="dashboard-content">
      <!-- Stats Cards with animations -->
      <div class="stats-grid">
        <div 
          v-for="(stat, index) in stats" 
          :key="stat.label"
          class="stat-card"
          :style="{ '--delay': index * 0.1 + 's', '--glow': stat.color }"
        >
          <div class="stat-icon-wrapper">
            <span class="stat-icon">{{ stat.icon }}</span>
            <div class="stat-glow"></div>
          </div>
          <div class="stat-info">
            <div class="stat-value" :style="{ color: stat.color }">
              <span class="counter">{{ stat.value }}</span>
            </div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
          <div class="stat-trend" v-if="stat.trend">
            <span :class="stat.trend > 0 ? 'up' : 'down'">
              {{ stat.trend > 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
            </span>
          </div>
        </div>
      </div>
      
      <!-- Charts Row with glass cards -->
      <div class="charts-row">
        <AppCard title="结果趋势 (7日)" class="chart-card" glow>
          <CurveChart
            :curves="trendCurves"
            xAxisLabel="日期"
            yAxisLabel="数量"
            height="300px"
          />
        </AppCard>
        
        <AppCard title="工艺类型分布" class="distribution-card">
          <div class="craft-distribution">
            <div 
              v-for="(craft, index) in craftTypes" 
              :key="craft.name" 
              class="craft-item"
              :style="{ '--delay': index * 0.1 + 's' }"
            >
              <div class="craft-header">
                <span class="craft-color" :style="{ background: craft.color }"></span>
                <span class="craft-name">{{ craft.name }}</span>
                <span class="craft-count">{{ craft.count.toLocaleString() }}</span>
              </div>
              <div class="craft-bar">
                <div 
                  class="craft-progress" 
                  :style="{ width: craft.percent + '%', background: craft.color }"
                ></div>
              </div>
              <div class="craft-percent">{{ craft.percent }}%</div>
            </div>
          </div>
        </AppCard>
      </div>
      
      <!-- Device Quick Access -->
      <AppCard title="设备快速访问" class="devices-preview">
        <template #header>
          <router-link to="/devices" class="view-all">查看全部 →</router-link>
        </template>
        <div class="devices-scroll">
          <div 
            v-for="device in topDevices" 
            :key="device.device_name"
            class="device-mini-card"
            @click="$router.push(`/devices/${encodeURIComponent(device.device_name)}`)"
          >
            <div class="device-mini-status" :class="device.status"></div>
            <div class="device-mini-name">{{ device.device_name }}</div>
            <div class="device-mini-rate" :class="{ good: device.ok_rate >= 95 }">
              {{ device.ok_rate?.toFixed(1) || 0 }}%
            </div>
          </div>
        </div>
      </AppCard>
      
      <!-- Recent Alarms with enhanced styling -->
      <AppCard title="最新报警" class="alarms-card">
        <template #header>
          <router-link to="/alarms" class="view-all">查看全部 →</router-link>
        </template>
        <div class="alarms-list">
          <transition-group name="alarm">
            <div v-for="alarm in recentAlarms" :key="alarm.id" class="alarm-item">
              <div class="alarm-indicator" :class="alarm.alarm_level?.toLowerCase()"></div>
              <AppBadge :type="alarm.alarm_level === 'ERROR' ? 'error' : 'warning'" size="sm">
                {{ alarm.alarm_level }}
              </AppBadge>
              <span class="alarm-code">{{ alarm.alarm_code }}</span>
              <span class="alarm-msg">{{ alarm.alarm_msg }}</span>
              <span class="alarm-time">{{ formatTime(alarm.create_time) }}</span>
            </div>
          </transition-group>
          <div v-if="recentAlarms.length === 0" class="empty-state">
            <span class="empty-icon">✓</span>
            <span>暂无报警记录</span>
          </div>
        </div>
      </AppCard>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppHeader from '../components/layout/AppHeader.vue'
import AppCard from '../components/common/AppCard.vue'
import AppBadge from '../components/common/AppBadge.vue'
import CurveChart from '../components/charts/CurveChart.vue'
import { getStats, getAlarms, getDevices } from '../api'

const stats = ref([
  { icon: '📊', label: '总结果数', value: '-', color: '#6366F1', trend: null },
  { icon: '✅', label: 'OK 数量', value: '-', color: '#10B981', trend: null },
  { icon: '❌', label: 'NOK 数量', value: '-', color: '#EF4444', trend: null },
  { icon: '🔔', label: '报警数', value: '-', color: '#F59E0B', trend: null }
])

const trendCurves = ref([])
const craftTypes = ref([])
const recentAlarms = ref([])
const topDevices = ref([])

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000 / 60)
  if (diff < 60) return `${diff}分钟前`
  if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(async () => {
  try {
    const data = await getStats()
    stats.value[0].value = data.total_count?.toLocaleString() || '0'
    stats.value[1].value = data.ok_count?.toLocaleString() || '0'
    stats.value[2].value = data.nok_count?.toLocaleString() || '0'
    stats.value[3].value = data.alarm_count?.toLocaleString() || '0'
    
    if (data.trend) {
      trendCurves.value = [{
        name: '结果数',
        x: data.trend.dates,
        y: data.trend.counts,
        color: '#6366F1',
        showArea: true
      }]
    }
    
    if (data.craft_distribution) {
      const total = data.craft_distribution.reduce((s, c) => s + c.count, 0)
      const colors = ['#6366F1', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6']
      craftTypes.value = data.craft_distribution.map((c, i) => ({
        name: c.craft_type,
        count: c.count,
        percent: Math.round(c.count / total * 100),
        color: colors[i % colors.length]
      }))
    }
  } catch (e) {
    console.error('Failed to load stats:', e)
  }
  
  try {
    const data = await getAlarms({ limit: 5 })
    recentAlarms.value = data.items || []
  } catch (e) {
    console.error('Failed to load alarms:', e)
  }
  
  try {
    const data = await getDevices()
    topDevices.value = (data.items || []).slice(0, 6)
  } catch (e) {
    console.error('Failed to load devices:', e)
  }
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
}

.dashboard-content {
  padding: var(--space-6) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Live Indicator */
.live-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: rgba(16, 185, 129, 0.15);
  border-radius: var(--radius-full);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.live-dot {
  width: 8px;
  height: 8px;
  background: var(--color-success);
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
  box-shadow: 0 0 10px var(--color-success);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.live-text {
  font-size: var(--font-size-sm);
  color: var(--color-success);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-5);
}

.stat-card {
  position: relative;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  animation: fadeInUp 0.6s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
  transform: translateY(20px);
  overflow: hidden;
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--glow);
}

.stat-icon-wrapper {
  position: relative;
}

.stat-icon {
  font-size: 36px;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}

.stat-glow {
  position: absolute;
  inset: -10px;
  background: var(--glow);
  filter: blur(20px);
  opacity: 0.3;
  border-radius: 50%;
  animation: glow 3s ease-in-out infinite alternate;
}

@keyframes glow {
  from { opacity: 0.2; }
  to { opacity: 0.4; }
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.stat-trend {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.stat-trend .up { color: var(--color-success); }
.stat-trend .down { color: var(--color-error); }

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-5);
}

.chart-card {
  min-height: 380px;
}

.distribution-card {
  min-height: 380px;
}

.craft-distribution {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-4) 0;
}

.craft-item {
  animation: fadeInUp 0.5s ease forwards;
  animation-delay: var(--delay);
  opacity: 0;
}

.craft-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.craft-color {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-xs);
}

.craft-name {
  flex: 1;
  font-size: var(--font-size-md);
  color: var(--text-primary);
}

.craft-count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.craft-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.craft-progress {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 1s ease;
  box-shadow: 0 0 10px currentColor;
}

.craft-percent {
  margin-top: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-align: right;
}

/* Devices Preview */
.devices-preview {
  overflow: hidden;
}

.devices-scroll {
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  padding: var(--space-2) 0;
}

.device-mini-card {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  min-width: 180px;
}

.device-mini-card:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(99, 102, 241, 0.5);
  transform: translateY(-2px);
}

.device-mini-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}

.device-mini-status.error {
  background: var(--color-error);
}

.device-mini-name {
  flex: 1;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-mini-rate {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: var(--text-secondary);
}

.device-mini-rate.good {
  color: var(--color-success);
}

.view-all {
  font-size: var(--font-size-sm);
  color: var(--color-primary-light);
}

/* Alarms */
.alarms-card {
  overflow: hidden;
}

.alarms-list {
  display: flex;
  flex-direction: column;
}

.alarm-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.alarm-item:last-child {
  border-bottom: none;
}

.alarm-indicator {
  position: absolute;
  left: -20px;
  width: 4px;
  height: 100%;
  border-radius: var(--radius-full);
}

.alarm-indicator.error { background: var(--color-error); }
.alarm-indicator.warning { background: var(--color-warning); }

.alarm-code {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  min-width: 80px;
}

.alarm-msg {
  flex: 1;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alarm-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  white-space: nowrap;
}

/* Alarm transition */
.alarm-enter-active,
.alarm-leave-active {
  transition: all 0.3s ease;
}

.alarm-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.alarm-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.empty-icon {
  width: 32px;
  height: 32px;
  background: rgba(16, 185, 129, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-success);
}
</style>
