<template>
  <div class="combined-curve-chart">
    <div class="chart-header">
      <div class="step-legend">
        <span 
          v-for="step in uniqueSteps" 
          :key="step"
          class="step-tag"
          :class="{ active: selectedSteps.includes(step) }"
          @click="toggleStep(step)"
        >
          Step {{ step }}
        </span>
      </div>
      <div class="curve-legend">
        <span 
          v-for="type in curveTypes" 
          :key="type.name"
          class="curve-tag"
          :class="{ active: selectedTypes.includes(type.name) }"
          :style="{ '--color': type.color }"
          @click="toggleType(type.name)"
        >
          <span class="curve-dot"></span>
          {{ type.name }}
        </span>
      </div>
    </div>
    <v-chart :option="chartOptions" autoresize class="chart" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { 
  TitleComponent, 
  TooltipComponent, 
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent
])

const props = defineProps({
  curves: {
    type: Array,
    default: () => []
  },
  steps: {
    type: Array,
    default: () => []
  },
  height: {
    type: String,
    default: '400px'
  }
})

const curveColors = {
  'TORQUE': '#6366F1',
  'ANGLE': '#10B981',
  'DEPTH': '#F59E0B',
  'SPEED': '#EC4899',
  'PRESSURE': '#3B82F6',
  'FORCE': '#8B5CF6',
  'STROKE': '#06B6D4'
}

const uniqueSteps = computed(() => {
  const steps = new Set(props.curves.map(c => c.step))
  return [...steps].sort((a, b) => a - b)
})

const curveTypes = computed(() => {
  const types = new Set(props.curves.map(c => c.curve_type))
  return [...types].map(t => ({
    name: t,
    color: curveColors[t] || '#6366F1'
  }))
})

const selectedSteps = ref([])
const selectedTypes = ref([])

// Initialize with all selected
if (uniqueSteps.value.length > 0) {
  selectedSteps.value = [...uniqueSteps.value]
}
if (curveTypes.value.length > 0) {
  selectedTypes.value = curveTypes.value.map(t => t.name)
}

const toggleStep = (step) => {
  const idx = selectedSteps.value.indexOf(step)
  if (idx >= 0) {
    selectedSteps.value.splice(idx, 1)
  } else {
    selectedSteps.value.push(step)
  }
}

const toggleType = (type) => {
  const idx = selectedTypes.value.indexOf(type)
  if (idx >= 0) {
    selectedTypes.value.splice(idx, 1)
  } else {
    selectedTypes.value.push(type)
  }
}

const filteredCurves = computed(() => {
  return props.curves.filter(c => 
    selectedSteps.value.includes(c.step) && 
    selectedTypes.value.includes(c.curve_type)
  )
})

const chartOptions = computed(() => {
  const series = filteredCurves.value.map(curve => ({
    name: `${curve.curve_type} (Step ${curve.step})`,
    type: 'line',
    data: curve.data_points?.y?.map((y, i) => [curve.data_points.x[i], y]) || [],
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 2,
      color: curveColors[curve.curve_type] || '#6366F1'
    },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: `${curveColors[curve.curve_type] || '#6366F1'}30` },
          { offset: 1, color: `${curveColors[curve.curve_type] || '#6366F1'}05` }
        ]
      }
    }
  }))
  
  // Step separator lines
  const stepMarks = props.steps.map((step, idx) => ({
    name: `Step ${step.step_index}`,
    xAxis: step.start_time
  }))
  
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 26, 36, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: 'rgba(255, 255, 255, 0.9)' }
    },
    legend: {
      bottom: 10,
      textStyle: {
        fontSize: 11,
        color: 'rgba(255, 255, 255, 0.6)'
      }
    },
    grid: {
      left: 60,
      right: 30,
      top: 20,
      bottom: 80
    },
    xAxis: {
      type: 'value',
      name: 'Time (s)',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { color: 'rgba(255, 255, 255, 0.5)' },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)' },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'Value',
      nameLocation: 'middle',
      nameGap: 45,
      nameTextStyle: { color: 'rgba(255, 255, 255, 0.5)' },
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)' },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)', type: 'dashed' } }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 45,
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        borderColor: 'transparent',
        fillerColor: 'rgba(99, 102, 241, 0.3)',
        handleStyle: { color: '#6366F1' },
        textStyle: { color: 'rgba(255, 255, 255, 0.5)' }
      }
    ],
    series
  }
})
</script>

<style scoped>
.combined-curve-chart {
  height: v-bind(height);
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
  gap: var(--space-3);
}

.step-legend,
.curve-legend {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.step-tag,
.curve-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.step-tag:hover,
.curve-tag:hover {
  background: rgba(255, 255, 255, 0.1);
}

.step-tag.active {
  background: var(--gradient-primary);
  border-color: transparent;
  color: white;
}

.curve-tag.active {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--color);
  color: var(--text-primary);
}

.curve-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color);
  box-shadow: 0 0 6px var(--color);
}

.chart {
  flex: 1;
  min-height: 0;
}
</style>
