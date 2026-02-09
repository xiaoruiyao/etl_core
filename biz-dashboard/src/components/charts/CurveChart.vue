<template>
  <div class="curve-chart">
    <v-chart :option="chartOptions" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { 
  TitleComponent, 
  TooltipComponent, 
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
])

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  curves: {
    type: Array,
    default: () => []
  },
  xAxisLabel: {
    type: String,
    default: 'Time (s)'
  },
  yAxisLabel: {
    type: String,
    default: 'Value'
  },
  height: {
    type: String,
    default: '300px'
  }
})

const chartOptions = computed(() => ({
  backgroundColor: 'transparent',
  title: {
    text: props.title,
    left: 'center',
    textStyle: {
      fontSize: 14,
      fontWeight: 600,
      color: 'rgba(255, 255, 255, 0.9)'
    }
  },
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(26, 26, 36, 0.95)',
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderWidth: 1,
    textStyle: {
      color: 'rgba(255, 255, 255, 0.9)'
    },
    axisPointer: {
      type: 'cross',
      lineStyle: {
        color: 'rgba(99, 102, 241, 0.5)'
      }
    }
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
    right: 20,
    top: 50,
    bottom: 60
  },
  xAxis: {
    type: 'category',
    name: props.xAxisLabel,
    nameLocation: 'middle',
    nameGap: 30,
    nameTextStyle: {
      color: 'rgba(255, 255, 255, 0.5)'
    },
    data: props.curves[0]?.x || [],
    axisLine: {
      lineStyle: { color: 'rgba(255, 255, 255, 0.1)' }
    },
    axisLabel: {
      color: 'rgba(255, 255, 255, 0.5)'
    },
    splitLine: {
      show: false
    }
  },
  yAxis: {
    type: 'value',
    name: props.yAxisLabel,
    nameLocation: 'middle',
    nameGap: 45,
    nameTextStyle: {
      color: 'rgba(255, 255, 255, 0.5)'
    },
    axisLine: {
      lineStyle: { color: 'rgba(255, 255, 255, 0.1)' }
    },
    axisLabel: {
      color: 'rgba(255, 255, 255, 0.5)'
    },
    splitLine: {
      lineStyle: { 
        color: 'rgba(255, 255, 255, 0.05)',
        type: 'dashed'
      }
    }
  },
  dataZoom: [
    {
      type: 'inside',
      start: 0,
      end: 100
    },
    {
      type: 'slider',
      start: 0,
      end: 100,
      height: 20,
      bottom: 35,
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
      borderColor: 'transparent',
      fillerColor: 'rgba(99, 102, 241, 0.3)',
      handleStyle: {
        color: '#6366F1'
      },
      textStyle: {
        color: 'rgba(255, 255, 255, 0.5)'
      }
    }
  ],
  series: props.curves.map(curve => ({
    name: curve.name,
    type: 'line',
    data: curve.y,
    smooth: true,
    symbol: 'none',
    lineStyle: {
      width: 2,
      color: curve.color || '#6366F1'
    },
    areaStyle: curve.showArea ? {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: `${curve.color || '#6366F1'}40` },
          { offset: 1, color: `${curve.color || '#6366F1'}05` }
        ]
      }
    } : undefined
  }))
}))
</script>

<style scoped>
.curve-chart {
  width: 100%;
  height: v-bind(height);
}
</style>
