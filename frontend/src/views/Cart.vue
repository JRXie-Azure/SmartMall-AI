<template>
  <div class="cart-page container">
    <h1 class="page-title">我的购物车</h1>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="cart.items.length === 0" class="empty-cart">
      <span class="empty-icon">🛒</span>
      <p>购物车是空的</p>
      <router-link to="/products"><el-button type="primary">去逛逛</el-button></router-link>
    </div>

    <div v-else class="cart-content">
      <div class="cart-list">
        <div v-for="item in cart.items" :key="item.id" class="cart-item card">
          <router-link :to="`/product/${item.product.id}`" class="item-img">
            <img :src="item.product.image" :alt="item.product.name" />
          </router-link>
          <div class="item-info">
            <router-link :to="`/product/${item.product.id}`" class="item-name">{{ item.product.name }}</router-link>
            <span class="item-price">¥{{ item.product.price }}</span>
          </div>
          <div class="item-qty">
            <el-input-number v-model="item.quantity" :min="1" :max="item.product.stock" size="small" @change="(v) => cart.updateItem(item.id, v)" />
          </div>
          <div class="item-subtotal">¥{{ (item.product.price * item.quantity).toFixed(2) }}</div>
          <el-button type="danger" link @click="cart.removeItem(item.id)">删除</el-button>
        </div>
      </div>

      <div class="cart-summary card">
        <div class="summary-row">
          <span>商品合计</span>
          <span class="total-price">¥{{ cart.totalPrice.toFixed(2) }}</span>
        </div>
        <!-- 优惠券 -->
      <div class="coupon-section" style="margin-bottom:12px">
        <el-input
          v-model="couponCode"
          placeholder="输入优惠码"
          size="small"
          style="width:160px"
          :disabled="couponApplied"
        />
        <el-button size="small" @click="applyCoupon" :loading="couponLoading" :disabled="couponApplied">
          {{ couponApplied ? '已使用' : '应用' }}
        </el-button>
        <span v-if="couponApplied" style="color:#e74c3c;font-size:13px;margin-left:8px">
          -¥{{ couponDiscount }}
        </span>
      </div>

      <el-button type="primary" size="large" style="width:100%;margin-top:16px" @click="checkout">立即结算</el-button>
      <div v-if="couponApplied" class="summary-row" style="margin-top:8px">
        <span>实付金额</span>
        <span class="total-price" style="color:#e74c3c">¥{{ Math.max(0, (cart.totalPrice - couponDiscount)).toFixed(2) }}</span>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '../stores/cart'
import { ordersAPI, couponAPI } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const cart = useCartStore()
const loading = ref(true)
const couponCode = ref('')
const couponApplied = ref(false)
const couponDiscount = ref(0)
const couponLoading = ref(false)

async function applyCoupon() {
  if (!couponCode.value.trim()) { ElMessage.warning('请输入优惠码'); return }
  couponLoading.value = true
  try {
    const res = await couponAPI.apply(couponCode.value.trim(), cart.totalPrice)
    couponDiscount.value = res.data?.discount || 0
    couponApplied.value = true
    ElMessage.success(`优惠 ¥${couponDiscount.value}`)
  } catch (e) {
    ElMessage.error('优惠码无效')
  }
  couponLoading.value = false
}

async function checkout() {
  try {
    const res = await ordersAPI.create({ note: '', coupon_code: couponApplied.value ? couponCode.value.trim() : null })
    const orderId = res.data?.id || res.data?.order?.id
    ElMessage.success('下单成功，即将跳转支付...')
    await cart.fetchCart()
    couponCode.value = ''
    couponApplied.value = false
    couponDiscount.value = 0
    router.push(`/pay/${orderId}`)
  } catch (e) {
    ElMessage.error('下单失败，请重试')
  }
}

onMounted(async () => {
  await cart.fetchCart()
  loading.value = false
})
</script>

<style scoped>
.cart-page { padding: 40px 0 60px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.empty-cart { text-align: center; padding: 80px 0; }
.empty-icon { font-size: 64px; display: block; margin-bottom: 12px; }
.empty-cart p { font-size: 16px; color: var(--text-light); margin-bottom: 16px; }

.cart-content { display: flex; gap: 24px; align-items: flex-start; }
.cart-list { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.cart-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}
.item-img { width: 80px; height: 80px; border-radius: 8px; overflow: hidden; flex-shrink: 0; }
.item-img img { width: 100%; height: 100%; object-fit: cover; }
.item-info { flex: 1; min-width: 0; }
.item-name { font-size: 14px; font-weight: 600; display: block; margin-bottom: 4px; }
.item-price { font-size: 16px; font-weight: 700; color: var(--accent); }
.item-qty { width: 120px; }
.item-subtotal { font-size: 16px; font-weight: 700; white-space: nowrap; }

.cart-summary {
  width: 300px;
  padding: 24px;
  position: sticky;
  top: 80px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 14px;
}
.total-price { font-size: 22px; font-weight: 700; color: var(--accent); }

@media (max-width: 768px) {
  .cart-content { flex-direction: column; }
  .cart-summary { width: 100%; position: static; }
}
</style>
