<template>
  <div class="home">
    <!-- Hero -->
    <section class="hero gradient-bg">
      <div class="container hero-inner">
        <div class="hero-text">
          <h1 class="hero-title">
            <span class="text-gradient">AI 赋能</span> 智能购物
          </h1>
          <p class="hero-subtitle">融合大模型对话、RAG 知识库和协同过滤推荐，让每一次购物都恰到好处</p>
          <div class="hero-actions">
            <router-link to="/products"><el-button type="primary" size="large" round>开始购物</el-button></router-link>
            <router-link to="/ai-chat"><el-button size="large" round class="btn-outline">体验 AI 助手</el-button></router-link>
          </div>
          <div class="hero-stats">
            <div class="stat-item">
              <span class="stat-num">16</span>
              <span class="stat-label">精选商品</span>
            </div>
            <div class="stat-item">
              <span class="stat-num">4</span>
              <span class="stat-label">商品分类</span>
            </div>
            <div class="stat-item">
              <span class="stat-num">AI</span>
              <span class="stat-label">智能推荐</span>
            </div>
          </div>
        </div>
        <div class="hero-visual">
          <div class="hero-circle">
            <span class="hero-emoji">🛒</span>
          </div>
          <div class="floating-card card-1">
            <img src="https://images.unsplash.com/photo-1542291026-7eec264c27ff" alt="运动鞋" />
          </div>
          <div class="floating-card card-2">
            <img src="https://images.unsplash.com/photo-1523275335684-37898b6baf30" alt="手表" />
          </div>
          <div class="floating-card card-3">
            <img src="https://images.unsplash.com/photo-1505740420928-5e560c06d30e" alt="耳机" />
          </div>
        </div>
      </div>
    </section>

    <!-- Featured -->
    <section class="section container">
      <div class="section-header">
        <h2>🔥 AI 精选推荐</h2>
        <router-link to="/products" class="view-all">查看全部 →</router-link>
      </div>
      <div v-if="loading" class="loading-grid">
        <el-skeleton v-for="n in 8" :key="n" animated>
          <template #template>
            <el-skeleton-item variant="image" style="width:100%;aspect-ratio:1" />
            <el-skeleton-item variant="text" style="width:60%" />
            <el-skeleton-item variant="text" style="width:40%" />
          </template>
        </el-skeleton>
      </div>
      <div v-else class="product-grid">
        <ProductCard v-for="p in featuredProducts" :key="p.id" :product="p" />
      </div>
    </section>

    <!-- Categories -->
    <section class="section container">
      <div class="section-header">
        <h2>📂 商品分类</h2>
      </div>
      <div class="category-grid">
        <router-link v-for="cat in categories" :key="cat.id" :to="`/products?category=${cat.id}`" class="category-card card">
          <span class="cat-icon">{{ catIcons[cat.id % catIcons.length] }}</span>
          <span class="cat-name">{{ cat.name }}</span>
        </router-link>
      </div>
    </section>

    <!-- Stats Banner -->
    <section class="stats-banner gradient-bg">
      <div class="container">
        <div class="stats-grid">
          <div class="stat-card" v-for="s in stats" :key="s.label">
            <span class="s-num">{{ s.num }}</span>
            <span class="s-label">{{ s.label }}</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { productsAPI } from '../api'
import ProductCard from '../components/ProductCard.vue'

const featuredProducts = ref([])
const categories = ref([])
const loading = ref(true)
const catIcons = ['👟', '💻', '👕', '⌚']

const stats = [
  { num: '16+', label: '精选商品' },
  { num: '4', label: '商品分类' },
  { num: 'AI', label: '智能推荐引擎' },
  { num: '24/7', label: 'AI 客服在线' }
]

onMounted(async () => {
  try {
    const [prodRes, catRes] = await Promise.all([
      productsAPI.getList({ page_size: 8, sort: 'sales' }),
      productsAPI.getCategories()
    ])
    featuredProducts.value = prodRes.data || []
    categories.value = catRes.data || []
  } catch (e) {
    console.error('Failed to load home data:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.hero {
  padding: 60px 0 80px;
  color: white;
  overflow: hidden;
  position: relative;
}
.hero::after {
  content: '';
  position: absolute;
  bottom: -40px;
  left: 0;
  right: 0;
  height: 80px;
  background: var(--bg);
  border-radius: 50% 50% 0 0;
}
.hero-inner {
  display: flex;
  align-items: center;
  gap: 60px;
  position: relative;
  z-index: 1;
}
.hero-text { flex: 1; }
.hero-title {
  font-size: 42px;
  font-weight: 800;
  margin-bottom: 16px;
  line-height: 1.2;
}
.hero-subtitle {
  font-size: 16px;
  color: rgba(255,255,255,0.75);
  margin-bottom: 32px;
  line-height: 1.6;
}
.hero-actions { display: flex; gap: 12px; margin-bottom: 40px; }
.btn-outline {
  border: 2px solid rgba(255,255,255,0.3) !important;
  color: white !important;
  background: transparent !important;
}
.btn-outline:hover { border-color: white !important; background: rgba(255,255,255,0.1) !important; }
.hero-stats { display: flex; gap: 40px; }
.stat-item { text-align: center; }
.stat-num { font-size: 28px; font-weight: 700; display: block; }
.stat-label { font-size: 13px; color: rgba(255,255,255,0.65); }

.hero-visual {
  flex: 0 0 400px;
  height: 400px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-circle {
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(255,255,255,0.2);
  animation: float 6s ease-in-out infinite;
}
.hero-emoji { font-size: 80px; }
.floating-card {
  position: absolute;
  width: 80px;
  height: 80px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.floating-card img { width: 100%; height: 100%; object-fit: cover; }
.card-1 { top: 20px; right: 20px; animation: floatCard 3s ease-in-out infinite; }
.card-2 { bottom: 40px; right: 60px; animation: floatCard 3.5s ease-in-out 0.5s infinite; }
.card-3 { bottom: 80px; left: 30px; animation: floatCard 4s ease-in-out 1s infinite; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}
@keyframes floatCard {
  0%, 100% { transform: translateY(0) rotate(-3deg); }
  50% { transform: translateY(-10px) rotate(0deg); }
}

.section { padding: 60px 0; }
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.section-header h2 { font-size: 22px; font-weight: 700; }
.view-all { font-size: 14px; color: var(--primary); font-weight: 500; }

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
.loading-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px;
  cursor: pointer;
}
.cat-icon { font-size: 32px; }
.cat-name { font-size: 14px; font-weight: 600; color: var(--text); }

.stats-banner { padding: 48px 0; margin-top: 40px; }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
  text-align: center;
}
.s-num { font-size: 32px; font-weight: 800; color: white; display: block; margin-bottom: 4px; }
.s-label { font-size: 13px; color: rgba(255,255,255,0.65); }

@media (max-width: 768px) {
  .hero-inner { flex-direction: column; }
  .hero-visual { flex: 0 0 200px; height: 200px; }
  .hero-circle { width: 150px; height: 150px; }
  .hero-title { font-size: 28px; }
  .product-grid, .loading-grid, .category-grid { grid-template-columns: repeat(2, 1fr); }
  .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 20px; }
}
</style>
