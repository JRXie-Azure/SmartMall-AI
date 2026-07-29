<template>
  <div class="ai-section">
    <!-- 销售预测 -->
    <div class="chart-card card" style="margin-bottom:16px">
      <h3>销售趋势预测（未来3天）</h3>
      <v-chart class="chart" :option="aiForecastOption" autoresize />
    </div>

    <!-- 用户画像 -->
    <div class="stats-row" style="margin-bottom:16px">
      <div class="stat-card card">
        <span class="sc-icon">👥</span>
        <div class="sc-info">
          <span class="sc-value">{{ aiData.user_profile?.total_users || 0 }}</span>
          <span class="sc-label">总用户</span>
        </div>
      </div>
      <div class="stat-card card">
        <span class="sc-icon">🆕</span>
        <div class="sc-info">
          <span class="sc-value">{{ aiData.user_profile?.new_users_7d || 0 }}</span>
          <span class="sc-label">7日新用户</span>
        </div>
      </div>
      <div class="stat-card card">
        <span class="sc-icon">🔄</span>
        <div class="sc-info">
          <span class="sc-value">{{ aiData.user_profile?.repurchase_rate || 0 }}%</span>
          <span class="sc-label">复购率</span>
        </div>
      </div>
      <div class="stat-card card">
        <span class="sc-icon">⭐</span>
        <div class="sc-info">
          <span class="sc-value">{{ aiData.user_profile?.old_users || 0 }}</span>
          <span class="sc-label">老用户</span>
        </div>
      </div>
    </div>

    <!-- AI 建议 -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="font-size:14px;margin-bottom:12px">🤖 AI 运营建议</h3>
      <el-timeline>
        <el-timeline-item v-for="(s, idx) in aiData.suggestions" :key="idx" type="primary">
          {{ s }}
        </el-timeline-item>
      </el-timeline>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="card">
          <h3 style="font-size:14px;margin-bottom:12px">⚠️ 滞销商品（30天销量&lt;5）</h3>
          <el-table :data="aiData.product_insights?.stagnant || []" size="small" stripe>
            <el-table-column prop="name" label="商品" show-overflow-tooltip />
            <el-table-column prop="sales" label="销量" width="70" />
            <el-table-column prop="stock" label="库存" width="70" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="card">
          <h3 style="font-size:14px;margin-bottom:12px">💡 潜力商品（高评分低销量）</h3>
          <el-table :data="aiData.product_insights?.potential || []" size="small" stripe>
            <el-table-column prop="name" label="商品" show-overflow-tooltip />
            <el-table-column prop="rating" label="评分" width="70" />
            <el-table-column prop="sales" label="销量" width="70" />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import VChart from 'vue-echarts'

defineProps({
  aiData: { type: Object, default: () => ({}) },
  aiForecastOption: { type: Object, default: () => ({}) },
})
</script>
