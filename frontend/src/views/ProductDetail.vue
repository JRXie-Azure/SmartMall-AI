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

    <template v-else-if="product">
      <div class="detail-content">
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

          <el-icon class="fav-btn" :class="{ active: isFavorite }" @click="toggleFavorite">
            <Star />
          </el-icon>

          <p class="info-desc">{{ product.description }}</p>

          <div v-if="variants.length > 0" class="sku-section">
            <div v-for="v in variants" :key="v.name" class="sku-group">
              <span class="sku-label">{{ v.name }}</span>
              <div class="sku-options">
                <el-button v-for="opt in v.options" :key="opt" size="small"
                  :type="selectedAttrs[v.name] === opt ? 'primary' : ''"
                  @click="selectedAttrs[v.name] = opt">{{ opt }}</el-button>
              </div>
            </div>
            <div v-if="selectedSku" class="sku-info">
              <span class="sku-price">¥{{ selectedSku.price || product.price }}</span>
              <span class="sku-stock">库存 {{ selectedSku.stock }} 件</span>
            </div>
          </div>

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

      <!-- 评价区域 -->
      <div class="reviews-section" v-if="reviews.length > 0 || reviewFormVisible">
        <h3 class="reviews-title">用户评价 ({{ reviews.length }})</h3>
        <div v-if="reviews.length === 0" class="no-reviews">暂无评价</div>
        <div v-else class="reviews-list">
          <div v-for="r in reviews" :key="r.id" class="review-item">
            <div class="review-header">
              <span class="review-user">{{ r.username || '匿名用户' }}</span>
              <el-rate :model-value="r.rating" disabled size="small" />
              <span class="review-date">{{ formatDate(r.created_at) }}</span>
            </div>
            <p class="review-content">{{ r.content }}</p>
          </div>
        </div>
        <el-button v-if="auth.isLoggedIn" type="primary" plain size="small" @click="reviewFormVisible = !reviewFormVisible" style="margin-top:12px">
          {{ reviewFormVisible ? '收起' : '写评价' }}
        </el-button>
        <!-- 评价表单 -->
        <div v-if="reviewFormVisible && auth.isLoggedIn" class="review-form">
          <el-rate v-model="reviewForm.rating" />
          <el-input v-model="reviewForm.content" type="textarea" :rows="3" placeholder="说说你的使用体验..." />
          <el-checkbox v-model="reviewForm.is_anonymous">匿名评价</el-checkbox>
          <el-button type="primary" size="small" @click="submitReview" :loading="reviewLoading">发表评价</el-button>
        </div>
      </div>
    </template>

    <div v-else class="not-found">
      <span class="nf-icon">🔍</span>
      <p>商品不存在</p>
      <router-link to="/products"><el-button type="primary">返回商品列表</el-button></router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI, skuAPI } from '../api'
import { useCartStore } from '../stores/cart'
import { useAuthStore } from '../stores/auth'
import { ShoppingCart, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const auth = useAuthStore()

const product = ref(null)
const loading = ref(true)
const quantity = ref(1)
const variants = ref([])
const skus = ref([])
const selectedAttrs = ref({})
const reviews = ref([])
const reviewFormVisible = ref(false)
const reviewForm = ref({ rating: 5, content: '', is_anonymous: false })
const reviewLoading = ref(false)
const isFavorite = ref(false)

const selectedSku = computed(() => {
  if (skus.value.length === 0) return null
  return skus.value.find(s => {
    const attrs = s.attributes || {}
    return Object.keys(selectedAttrs.value).every(
      k => selectedAttrs.value[k] === attrs[k]
    )
  })
})

async function loadProduct() {
  loading.value = true
  try {
    const [res, skuRes] = await Promise.all([
      productsAPI.getDetail(route.params.id),
      skuAPI.getByProduct(route.params.id).catch(() => ({ data: { variants: [], skus: [] } }))
    ])
    product.value = res.data
    variants.value = skuRes.data?.variants || []
    skus.value = skuRes.data?.skus || []
    // 默认选中第一个选项
    variants.value.forEach(v => {
      if (v.options?.length > 0) {
        selectedAttrs.value[v.name] = v.options[0]
      }
    })
    // 加载评价
    try {
      const reviewRes = await productsAPI.getReviews(route.params.id)
      reviews.value = reviewRes.data || []
    } catch { reviews.value = [] }
    // 检查收藏状态
    if (auth.isLoggedIn) {
      try {
        const favRes = await productsAPI.checkFavorite(route.params.id)
        isFavorite.value = favRes.data?.is_favorite || false
      } catch {}
    }
  } catch {
    product.value = null
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!auth.isLoggedIn) { router.push('/login'); return }
  try {
    const res = await productsAPI.addFavorite(product.value.id)
    isFavorite.value = res.data?.is_favorite || !isFavorite.value
    ElMessage.success(res.data?.message || '操作成功')
  } catch { ElMessage.error('操作失败') }
}

async function submitReview() {
  if (!reviewForm.value.content.trim()) { ElMessage.warning('请输入评价内容'); return }
  reviewLoading.value = true
  try {
    const res = await productsAPI.createReview(product.value.id, reviewForm.value)
    reviews.value.unshift(res.data)
    reviewForm.value = { rating: 5, content: '', is_anonymous: false }
    reviewFormVisible.value = false
    ElMessage.success('评价发表成功')
    // 刷新商品评分
    await loadProduct()
  } catch { ElMessage.error('评价失败') }
  reviewLoading.value = false
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
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
.sku-section { margin: 16px 0; }
.sku-group { margin-bottom: 12px; }
.sku-label { font-size: 13px; color: var(--text-light); margin-bottom: 6px; display: block; }
.sku-options { display: flex; flex-wrap: wrap; gap: 8px; }
.sku-info { margin-top: 8px; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; }
.sku-price { font-size: 18px; font-weight: 700; color: var(--accent); }
.sku-stock { font-size: 12px; color: var(--text-light); margin-left: 8px; }

.reviews-section { margin-top: 40px; background: white; border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow); }
.reviews-title { font-size: 18px; font-weight: 700; margin-bottom: 16px; }
.no-reviews { color: var(--text-light); text-align: center; padding: 32px; }
.reviews-list { display: flex; flex-direction: column; gap: 16px; }
.review-item { padding: 12px 0; border-bottom: 1px solid var(--border); }
.review-item:last-child { border-bottom: none; }
.review-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.review-user { font-weight: 600; font-size: 13px; }
.review-date { font-size: 12px; color: #bbb; margin-left: auto; }
.review-content { font-size: 14px; color: var(--text); line-height: 1.6; }
.review-form { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }

.fav-btn { cursor: pointer; font-size: 20px; transition: transform 0.2s; }
.fav-btn:hover { transform: scale(1.2); }
.fav-btn.active { color: var(--accent); }
</style>
