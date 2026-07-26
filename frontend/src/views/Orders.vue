<template>
  <div class="orders-page container">
    <h1 class="page-title">我的订单</h1>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="orders.length === 0" class="empty">
      <span class="empty-icon">📦</span>
      <p>还没有订单</p>
      <router-link to="/products"><el-button type="primary">去购物</el-button></router-link>
    </div>

    <div v-else class="orders-list">
      <div v-for="order in orders" :key="order.id" class="order-card card">
        <div class="order-header">
          <span class="order-id">订单号：{{ order.id }}</span>
          <el-tag :type="statusType(order.status)" size="small">{{ order.status }}</el-tag>
          <span class="order-date">{{ formatDate(order.created_at) }}</span>
        </div>
        <div class="order-items">
          <div v-for="item in order.items" :key="item.id" class="order-item">
            <img :src="item.product?.image" :alt="item.product?.name" class="oi-img" />
            <div class="oi-info">
              <span class="oi-name">{{ item.product?.name }}</span>
              <span class="oi-qty">x{{ item.quantity }}</span>
            </div>
            <span class="oi-price">¥{{ (item.price * item.quantity).toFixed(2) }}</span>
          </div>
        </div>
        <div class="order-footer">
          <span class="order-total">合计：<strong>¥{{ order.total_amount.toFixed(2) }}</strong></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ordersAPI } from '../api'

const orders = ref([])
const loading = ref(true)

const statusMap = {
  pending: '',
  paid: 'success',
  shipped: 'warning',
  completed: 'success',
  cancelled: 'danger'
}

function statusType(s) { return statusMap[s] || 'info' }

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

onMounted(async () => {
  try {
    const res = await ordersAPI.getList()
    orders.value = Array.isArray(res.data) ? res.data : (res.data?.items || [])
  } catch {}
  loading.value = false
})
</script>

<style scoped>
.orders-page { padding: 40px 0 60px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }
.empty { text-align: center; padding: 80px 0; }
.empty-icon { font-size: 64px; display: block; margin-bottom: 12px; }
.empty p { color: var(--text-light); margin-bottom: 16px; }

.orders-list { display: flex; flex-direction: column; gap: 16px; }
.order-card { padding: 16px 20px; }
.order-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}
.order-id { font-size: 13px; color: var(--text-light); }
.order-date { font-size: 12px; color: #bbb; margin-left: auto; }

.order-items { display: flex; flex-direction: column; gap: 8px; }
.order-item { display: flex; align-items: center; gap: 12px; }
.oi-img { width: 48px; height: 48px; border-radius: 6px; object-fit: cover; }
.oi-info { flex: 1; }
.oi-name { font-size: 13px; font-weight: 500; }
.oi-qty { font-size: 12px; color: var(--text-light); display: block; }
.oi-price { font-size: 14px; font-weight: 600; }

.order-footer { text-align: right; padding-top: 12px; border-top: 1px solid var(--border); margin-top: 12px; }
.order-total { font-size: 14px; }
.order-total strong { font-size: 18px; color: var(--accent); }
</style>
