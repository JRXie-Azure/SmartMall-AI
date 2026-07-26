<template>
  <div class="detail-page container">
    <div v-if="loading" class="loading-detail">
      <el-skeleton animated>
        <template #template>
          <div style="display:flex;gap:40px">
            <el-skeleton-item variant="image" style="width:400px;height:400px" />
            <div style="flex:1">
              <el-skeleton-item variant="text" style="width:60%;height:32px" />
              <el-skeleton-item variant="text" style="width:30%" />
              <el-skeleton-item variant="text" style="width:100%" />
              <el-skeleton-item variant="text" style="width:100%" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <div v-else-if="product" class="detail-content">
      <div class="detail-gallery">
        <img :src="product.image" :alt="product.name" class="main-img" />
      </div>

      <div class="detail-info">
        <div class="info-brand">{{ product.brand || 'SmartMall' }}</div>
        <h1 class="info-name">{{ product.name }}</h1>

        <div class="info-rating">
          <el-rate :model-value="product.rating" disabled show-score text-color="#F39C12" />
          <span class="sales-text">已售 {{ product.sales }} 件</span>
        </div>

        <div class="info-price">
          <span class="current-price">¥{{ product.price }}</span>
          <span v-if="product.original_price > product.price" class="original-price">¥{{ product.original_price }}</span>
          <span v-if="product.is_sale" class="discount-tag">优惠中</span>
        </div>

        <div class="info-tags">
          <el-tag v-if="product.is_recommend" type="danger">AI 推荐</el-tag>
          <el-tag v-if="product.is_new" type="success">新品</el-tag>
          <el-tag v-if="product.is_sale" type="warning">特惠</el-tag>
        </div>

        <p class="info-desc">{{ product.description }}</p>

        <div class="info-stock">
          <span>库存：</span>
          <span :class="{ 'low-stock': product.stock < 10 }">{{ product.stock > 0 ? product.stock + ' 件' : '暂时缺货' }}</span>
        </div>

        <div class="info-actions">
          <el-input-number v-model="quantity" :min="1" :max="product.stock" :disabled="product.stock <= 0" />
          <el-button type="primary" size="large" :disabled="product.stock <= 0" @click="addToCart">
            <el-icon><ShoppingCart /></el-icon> 加入购物车
          </el-button>
          <el-button size="large" :disabled="product.stock <= 0" type="success" @click="buyNow">
            立即购买
          </el-button>
        </div>
      </div>
    </div>

    <div v-else class="not-found">
      <span class="nf-icon">🔍</span>
      <p>商品不存在</p>
      <router-link to="/products"><el-button type="primary">返回商品列表</el-button></router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '../api'
import { useCartStore } from '../stores/cart'
import { useAuthStore } from '../stores/auth'
import { ShoppingCart } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const auth = useAuthStore()

const product = ref(null)
const loading = ref(true)
const quantity = ref(1)

async function loadProduct() {
  loading.value = true
  try {
    const res = await productsAPI.getDetail(route.params.id)
    product.value = res.data
  } catch {
    product.value = null
  } finally {
    loading.value = false
  }
}

function addToCart() {
  if (!auth.isLoggedIn) { router.push('/login'); return }
  cart.addItem(product.value.id, quantity.value)
}

async function buyNow() {
  if (!auth.isLoggedIn) { router.push('/login'); return }
  await cart.addItem(product.value.id, quantity.value)
  router.push('/cart')
}

onMounted(loadProduct)
</script>

<style scoped>
.detail-page { padding: 40px 0 60px; }
.detail-content { display: flex; gap: 40px; background: white; border-radius: var(--radius); padding: 32px; box-shadow: var(--shadow); }
.detail-gallery { flex: 0 0 400px; }
.main-img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: var(--radius); }

.detail-info { flex: 1; }
.info-brand { font-size: 13px; color: var(--primary); font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
.info-name { font-size: 26px; font-weight: 700; margin-bottom: 12px; }
.info-rating { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.sales-text { font-size: 13px; color: var(--text-light); }

.info-price { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; padding: 16px; background: #FFF5F5; border-radius: 8px; }
.current-price { font-size: 30px; font-weight: 700; color: var(--accent); }
.original-price { font-size: 16px; color: #bbb; text-decoration: line-through; }
.discount-tag { font-size: 12px; background: var(--accent); color: white; padding: 2px 8px; border-radius: 4px; }

.info-tags { display: flex; gap: 8px; margin-bottom: 16px; }
.info-desc { font-size: 14px; color: var(--text-light); line-height: 1.8; margin-bottom: 16px; }
.info-stock { font-size: 13px; margin-bottom: 24px; color: var(--text-light); }
.low-stock { color: var(--accent); font-weight: 600; }

.info-actions { display: flex; gap: 12px; align-items: center; }

.not-found { text-align: center; padding: 80px 0; }
.nf-icon { font-size: 64px; display: block; margin-bottom: 16px; }

.loading-detail { padding: 40px; background: white; border-radius: var(--radius); }

@media (max-width: 768px) {
  .detail-content { flex-direction: column; }
  .detail-gallery { flex: none; width: 100%; }
  .info-actions { flex-wrap: wrap; }
}
</style>
