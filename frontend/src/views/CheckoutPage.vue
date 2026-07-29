<template>
  <div class="checkout-page container">
    <h1 class="page-title">确认支付</h1>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="!order" class="empty-state">
      <p>订单不存在或已过期</p>
      <router-link to="/orders"><el-button type="primary">查看订单</el-button></router-link>
    </div>

    <div v-else class="checkout-content">
      <!-- 订单摘要 -->
      <div class="order-summary card">
        <h3>订单信息</h3>
        <div class="summary-rows">
          <div class="s-row"><span>订单编号</span><span>{{ order.order_no }}</span></div>
          <div class="s-row"><span>下单时间</span><span>{{ formatDate(order.created_at) }}</span></div>
          <div class="s-row"><span>商品数量</span><span>{{ order.items?.length || 0 }} 件</span></div>
          <div class="s-row total"><span>应付金额</span><span class="price">¥{{ order.total_amount?.toFixed(2) }}</span></div>
        </div>

        <div class="order-items">
          <div v-for="item in order.items" :key="item.product_name" class="o-item">
            <img :src="item.product_image" :alt="item.product_name" />
            <div class="o-info">
              <span class="o-name">{{ item.product_name }}</span>
              <span class="o-meta">x{{ item.quantity }} · ¥{{ item.price }}</span>
            </div>
            <span class="o-sub">¥{{ (item.price * item.quantity).toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <!-- 支付方式 -->
      <div class="payment-section card">
        <h3>选择支付方式</h3>
        <div class="pay-methods">
          <div
            v-for="m in payMethods"
            :key="m.value"
            class="pay-method"
            :class="{ active: payMethod === m.value }"
            @click="payMethod = m.value"
          >
            <span class="pm-icon">{{ m.icon }}</span>
            <div class="pm-info">
              <span class="pm-name">{{ m.label }}</span>
              <span class="pm-desc">{{ m.desc }}</span>
            </div>
            <el-icon v-if="payMethod === m.value" class="pm-check"><Check /></el-icon>
          </div>
        </div>

        <el-button
          type="primary"
          size="large"
          style="width:100%;margin-top:24px"
          @click="handlePay"
          :loading="paying"
        >
          {{ payMethod === 'mock' ? '确认支付' : '前往支付' }}
        </el-button>
      </div>
    </div>

    <!-- 支付结果弹窗 -->
    <el-dialog v-model="resultVisible" title="支付结果" width="360px" :close-on-click-modal="false" :show-close="false">
      <div class="result-content">
        <div v-if="paySuccess" class="result-success">
          <span class="result-icon">✓</span>
          <h3>支付成功</h3>
          <p>订单 {{ order?.order_no }} 已支付</p>
        </div>
        <div v-else class="result-fail">
          <span class="result-icon fail">✗</span>
          <h3>支付失败</h3>
          <p>{{ payError }}</p>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="goOrders">查看订单</el-button>
        <el-button v-if="!paySuccess" @click="resultVisible = false">重新支付</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ordersAPI, paymentAPI } from '../api'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const order = ref(null)
const loading = ref(true)
const paying = ref(false)
const payMethod = ref('mock')
const resultVisible = ref(false)
const paySuccess = ref(false)
const payError = ref('')

const payMethods = [
  { value: 'mock', label: '模拟支付', desc: '演示环境即时到账', icon: '💳' },
  { value: 'alipay', label: '支付宝', desc: '推荐支付宝用户使用', icon: '🔵' },
  { value: 'wechat', label: '微信支付', desc: '推荐微信用户使用', icon: '🟢' },
]

const orderId = computed(() => route.params.id)

function formatDate(d) {
  if (!d) return '-'
  return d.slice(0, 16).replace('T', ' ')
}

async function loadOrder() {
  loading.value = true
  try {
    const res = await ordersAPI.getDetail(orderId.value)
    order.value = res.data
    if (order.value?.status !== 'pending') {
      ElMessage.warning('该订单无需支付')
      router.replace('/orders')
    }
  } catch (e) {
    order.value = null
  } finally {
    loading.value = false
  }
}

async function handlePay() {
  paying.value = true
  try {
    if (payMethod.value === 'mock') {
      await paymentAPI.mockPay(orderId.value)
      paySuccess.value = true
    } else {
      await paymentAPI.create(orderId.value, payMethod.value)
      await new Promise(r => setTimeout(r, 1000))
      await paymentAPI.mockPay(orderId.value)
      paySuccess.value = true
    }
    resultVisible.value = true
  } catch (e) {
    paySuccess.value = false
    payError.value = e.response?.data?.detail || '支付失败，请重试'
    resultVisible.value = true
  } finally {
    paying.value = false
  }
}

function goOrders() {
  router.push('/orders')
}

onMounted(loadOrder)
</script>

<style scoped>
.checkout-page { padding: 40px 0 60px; max-width: 720px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.empty-state { text-align: center; padding: 80px 0; }
.empty-state p { font-size: 16px; color: var(--text-light); margin-bottom: 16px; }

.checkout-content { display: flex; flex-direction: column; gap: 20px; }

.order-summary { padding: 24px; }
.order-summary h3 { font-size: 16px; margin-bottom: 16px; }
.summary-rows { margin-bottom: 16px; }
.s-row { display: flex; justify-content: space-between; font-size: 14px; padding: 4px 0; color: #606266; }
.s-row.total { font-size: 16px; font-weight: 700; color: #303133; padding-top: 12px; border-top: 1px solid #f0f2f5; margin-top: 8px; }
.price { color: #e74c3c; font-size: 20px; }

.order-items { border-top: 1px solid #f0f2f5; padding-top: 12px; }
.o-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
.o-item img { width: 48px; height: 48px; border-radius: 6px; object-fit: cover; }
.o-info { flex: 1; display: flex; flex-direction: column; }
.o-name { font-size: 13px; font-weight: 600; }
.o-meta { font-size: 12px; color: #909399; }
.o-sub { font-size: 14px; font-weight: 600; }

.payment-section { padding: 24px; }
.payment-section h3 { font-size: 16px; margin-bottom: 16px; }
.pay-methods { display: flex; flex-direction: column; gap: 10px; }
.pay-method {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 10px;
  cursor: pointer;
  transition: all .2s;
}
.pay-method:hover { border-color: var(--primary); }
.pay-method.active { border-color: var(--primary); background: #f5f3ff; }
.pm-icon { font-size: 28px; }
.pm-info { flex: 1; display: flex; flex-direction: column; }
.pm-name { font-size: 14px; font-weight: 600; }
.pm-desc { font-size: 12px; color: #909399; }
.pm-check { color: var(--primary); font-size: 20px; }

.result-content { text-align: center; padding: 20px 0; }
.result-icon { display: inline-flex; align-items: center; justify-content: center; width: 56px; height: 56px; border-radius: 50%; font-size: 28px; font-weight: 700; margin-bottom: 12px; }
.result-success .result-icon { background: #f0fdf4; color: #16a34a; }
.result-fail .result-icon { background: #fef2f2; color: #e74c3c; }
.result-content h3 { font-size: 18px; margin: 8px 0 4px; }
.result-content p { font-size: 13px; color: #909399; }

@media (max-width: 768px) {
  .checkout-page { padding: 20px 12px; }
}
</style>