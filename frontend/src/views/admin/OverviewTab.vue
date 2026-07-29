<template>
  <div>
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div v-for="s in statsCards" :key="s.label" class="stat-card card">
        <span class="sc-icon">{{ s.icon }}</span>
        <div class="sc-info">
          <span class="sc-value">{{ s.value }}</span>
          <span class="sc-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- 告警栏 -->
    <div v-if="alerts.length" class="alert-bar">
      <el-alert
        v-for="a in alerts" :key="a.type + a.message"
        :title="a.message"
        :type="a.type"
        :closable="false"
        show-icon
        style="margin-bottom:8px"
      />
    </div>

    <div class="charts-row">
      <div class="chart-card card">
        <h3>销售趋势</h3>
        <v-chart class="chart" :option="salesOption" autoresize />
      </div>
      <div class="chart-card card">
        <h3>品类分布</h3>
        <v-chart class="chart" :option="categoryOption" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup>
import VChart from 'vue-echarts'

defineProps({
  statsCards: { type: Array, default: () => [] },
  alerts: { type: Array, default: () => [] },
  salesOption: { type: Object, default: () => ({}) },
  categoryOption: { type: Object, default: () => ({}) },
})
</script>
