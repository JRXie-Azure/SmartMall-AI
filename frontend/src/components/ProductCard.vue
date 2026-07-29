<template>
  <router-link :to="`/product/${product.id}`" class="product-card card">
    <div class="card-img">
      <img :src="product.image" :alt="product.name" loading="lazy" />
      <div class="card-tags">
        <span v-if="product.is_sale" class="tag sale">特惠</span>
        <span v-if="product.is_new" class="tag new">新品</span>
        <span v-if="product.is_recommend" class="tag ai">AI推荐</span>
      </div>
      <el-button class="quick-add" size="small" circle @click.prevent="handleAddCart">
        <el-icon><ShoppingCart /></el-icon>
      </el-button>
    </div>
    <div class="card-info">
      <span class="brand">{{ product.brand || 'SmartMall' }}</span>
      <h3 class="name">{{ product.name }}</h3>
      <div class="price-row">
        <span class="price">¥{{ product.price }}</span>
        <span v-if="product.original_price > product.price" class="original">¥{{ product.original_price }}</span>
      </div>
      <div class="card-footer">
        <span class="rating"><el-icon><StarFilled /></el-icon> {{ product.rating }}</span>
        <span class="sales">已售 {{ product.sales }}</span>
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { ShoppingCart, StarFilled } from '@element-plus/icons-vue'
import { useCartStore } from '../stores/cart'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

const props = defineProps({ product: Object })
const cart = useCartStore()
const auth = useAuthStore()

function handleAddCart() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  cart.addItem(props.product.id)
}
</script>

<style scoped>
.product-card {
  display: block;
  overflow: hidden;
  cursor: pointer;
}
.card-img {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: #F0F0F5;
}
.card-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s;
}
.product-card:hover .card-img img { transform: scale(1.08); }
.card-tags {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  gap: 4px;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  color: white;
}
.tag.sale { background: var(--accent); }
.tag.new { background: var(--success); }
.tag.ai { background: linear-gradient(135deg, #6C5CE7, #A29BFE); }
.quick-add {
  position: absolute;
  bottom: 8px;
  right: 8px;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.2s;
  background: white;
  color: var(--primary);
}
.product-card:hover .quick-add { opacity: 1; transform: translateY(0); }
.card-info { padding: 12px; }
.brand { font-size: 11px; color: var(--text-light); text-transform: uppercase; }
.name {
  font-size: 14px;
  font-weight: 600;
  margin: 4px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.price-row { display: flex; align-items: baseline; gap: 8px; margin-top: 4px; }
.price { font-size: 18px; font-weight: 700; color: var(--accent); }
.original { font-size: 13px; color: #bbb; text-decoration: line-through; }
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-light);
}
.rating { display: flex; align-items: center; gap: 2px; color: #F39C12; }
</style>
