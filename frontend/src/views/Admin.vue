<template>
  <div class="admin-page container">
    <h1 class="page-title">管理后台</h1>

    <!-- Stats Cards -->
    <div class="stats-row">
      <div v-for="s in statsCards" :key="s.label" class="stat-card card">
        <span class="sc-icon">{{ s.icon }}</span>
        <div class="sc-info">
          <span class="sc-value">{{ s.value }}</span>
          <span class="sc-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="chart-card card">
        <h3>📈 销售趋势</h3>
        <v-chart class="chart" :option="salesOption" autoresize />
      </div>
      <div class="chart-card card">
        <h3>🍩 品类分布</h3>
        <v-chart class="chart" :option="categoryOption" autoresize />
      </div>
    </div>

    <!-- Products Management -->
    <div class="card" style="margin-top:24px">
      <div class="card-header">
        <h3>商品管理</h3>
        <el-button type="primary" size="small" @click="openEdit(null)">添加商品</el-button>
      </div>
      <el-table :data="products" stripe style="width:100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="图片" width="80">
          <template #default="{row}">
            <img :src="row.image" style="width:40px;height:40px;object-fit:cover;border-radius:4px" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{row}">¥{{ row.price }}</template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="80" />
        <el-table-column prop="sales" label="销量" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '上架' : '下架' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{row}">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteProduct(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" :title="editingProduct?.id ? '编辑商品' : '添加商品'" width="500px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="商品名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="价格">
              <el-input-number v-model="editForm.price" :min="0" :step="0.01" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="库存">
              <el-input-number v-model="editForm.stock" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="图片URL">
          <el-input v-model="editForm.image" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProduct" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { adminAPI } from '../api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { ElMessage, ElMessageBox } from 'element-plus'

use([CanvasRenderer, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const statsCards = ref([
  { icon: '💰', label: '总销售额', value: '¥0' },
  { icon: '👥', label: '用户数', value: '0' },
  { icon: '📦', label: '订单数', value: '0' },
  { icon: '🛒', label: '商品数', value: '0' }
])

const salesOption = ref({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [], boundaryGap: false },
  yAxis: { type: 'value' },
  series: [{ data: [], type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: '#6C5CE7' } }]
})

const categoryOption = ref({
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['45%', '70%'], center: ['50%', '50%'],
    label: { show: true }, emphasis: { label: { fontSize: 16, fontWeight: 'bold' } },
    data: []
  }]
})

const products = ref([])
const editVisible = ref(false)
const editingProduct = ref(null)
const saving = ref(false)
const editForm = reactive({ name: '', description: '', price: 0, stock: 0, image: '' })

async function loadStats() {
  try {
    const [statsRes, chartsRes, prodsRes] = await Promise.all([
      adminAPI.getStats(),
      adminAPI.getCharts(),
      adminAPI.getProducts({ page_size: 100 })
    ])

    const s = statsRes.data
    statsCards.value = [
      { icon: '💰', label: '总销售额', value: '¥' + (s.total_revenue || 0).toFixed(2) },
      { icon: '👥', label: '用户数', value: String(s.total_users || 0) },
      { icon: '📦', label: '订单数', value: String(s.total_orders || 0) },
      { icon: '🛒', label: '商品数', value: String(s.total_products || 0) }
    ]

    const c = chartsRes.data
    if (c?.sales_trend) {
      salesOption.value.xAxis.data = c.sales_trend.map(i => i.date || '')
      salesOption.value.series[0].data = c.sales_trend.map(i => i.amount || 0)
    }
    if (c?.categories) {
      categoryOption.value.series[0].data = c.categories.map(i => ({ name: i.name, value: i.count }))
    }

    products.value = Array.isArray(prodsRes.data) ? prodsRes.data : (prodsRes.data?.items || [])
  } catch (e) {
    console.error('Admin data load failed:', e)
  }
}

function openEdit(product) {
  editingProduct.value = product
  if (product) {
    Object.assign(editForm, {
      name: product.name,
      description: product.description || '',
      price: product.price,
      stock: product.stock,
      image: product.image || ''
    })
  } else {
    Object.assign(editForm, { name: '', description: '', price: 0, stock: 0, image: '' })
  }
  editVisible.value = true
}

async function saveProduct() {
  saving.value = true
  try {
    if (editingProduct.value?.id) {
      await adminAPI.updateProduct(editingProduct.value.id, editForm)
      ElMessage.success('更新成功')
    } else {
      await adminAPI.createProduct(editForm)
      ElMessage.success('添加成功')
    }
    editVisible.value = false
    loadStats()
  } catch {} finally {
    saving.value = false
  }
}

async function deleteProduct(id) {
  try {
    await ElMessageBox.confirm('确定删除该商品？', '提示', { type: 'warning' })
    await adminAPI.deleteProduct(id)
    ElMessage.success('删除成功')
    loadStats()
  } catch {}
}

onMounted(loadStats)
</script>

<style scoped>
.admin-page { padding: 40px 0 60px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
}
.sc-icon { font-size: 32px; }
.sc-value { font-size: 22px; font-weight: 700; display: block; }
.sc-label { font-size: 12px; color: var(--text-light); }

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.chart-card { padding: 20px; }
.chart-card h3 { font-size: 14px; margin-bottom: 12px; }
.chart { height: 280px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 4px;
}
.card-header h3 { font-size: 14px; }

@media (max-width: 768px) {
  .stats-row, .charts-row { grid-template-columns: 1fr; }
}
</style>
