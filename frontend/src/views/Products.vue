<template>
  <div class="products-page container">
    <div class="page-header">
      <h1>全部商品</h1>
      <p>发现你的心仪好物</p>
    </div>

    <div class="filters-bar">
      <div class="search-box">
        <el-input v-model="keyword" placeholder="搜索商品..." clearable @clear="search" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="search">搜索</el-button>
      </div>
      <div class="filter-tags">
        <el-radio-group v-model="sort" @change="loadProducts">
          <el-radio-button value="sales">热销</el-radio-button>
          <el-radio-button value="price_asc">价格 ↑</el-radio-button>
          <el-radio-button value="price_desc">价格 ↓</el-radio-button>
          <el-radio-button value="rating">评分</el-radio-button>
          <el-radio-button value="newest">最新</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="products-layout">
      <aside class="sidebar">
        <h3>商品分类</h3>
        <el-menu :default-active="String(categoryId)" @select="handleCategoryChange">
          <el-menu-item index="0">全部分类</el-menu-item>
          <el-menu-item v-for="cat in categories" :key="cat.id" :index="String(cat.id)">
            {{ cat.name }}
          </el-menu-item>
        </el-menu>
      </aside>

      <div class="products-content">
        <div v-if="loading" class="loading-grid">
          <el-skeleton v-for="n in 8" :key="n" animated>
            <template #template>
              <el-skeleton-item variant="image" style="width:100%;aspect-ratio:1" />
              <el-skeleton-item variant="text" style="width:60%" />
              <el-skeleton-item variant="text" style="width:40%" />
            </template>
          </el-skeleton>
        </div>
        <div v-else-if="products.length === 0" class="empty">
          <span class="empty-icon">📭</span>
          <p>没有找到相关商品</p>
        </div>
        <div v-else class="product-grid">
          <ProductCard v-for="p in products" :key="p.id" :product="p" />
        </div>

        <div v-if="total > pageSize" class="pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="loadProducts"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsAPI } from '../api'
import { Search } from '@element-plus/icons-vue'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const router = useRouter()

const products = ref([])
const categories = ref([])
const loading = ref(true)
const page = ref(1)
const total = ref(0)
const pageSize = 12
const keyword = ref(route.query.keyword || '')
const sort = ref('sales')
const categoryId = ref(Number(route.query.category) || 0)

async function loadProducts() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, sort: sort.value }
    if (keyword.value) params.keyword = keyword.value
    if (categoryId.value) params.category_id = categoryId.value
    const res = await productsAPI.getList(params)
    products.value = Array.isArray(res.data) ? res.data : (res.data?.items || [])
    total.value = res.data?.total || products.value.length
  } catch (e) {
    products.value = []
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  router.replace({ query: { ...route.query, keyword: keyword.value || undefined } })
  loadProducts()
}

function handleCategoryChange(idx) {
  categoryId.value = Number(idx)
  page.value = 1
  loadProducts()
}

onMounted(async () => {
  try {
    const res = await productsAPI.getCategories()
    categories.value = res.data || []
  } catch {}
  loadProducts()
})

watch(sort, () => { page.value = 1; loadProducts() })
</script>

<style scoped>
.products-page { padding: 40px 0 60px; }
.page-header { margin-bottom: 28px; }
.page-header h1 { font-size: 28px; font-weight: 700; }
.page-header p { color: var(--text-light); font-size: 14px; margin-top: 4px; }

.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px;
  background: white;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.search-box { display: flex; gap: 8px; width: 320px; }

.products-layout { display: flex; gap: 24px; }
.sidebar {
  width: 180px;
  flex-shrink: 0;
  background: white;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 0;
}
.sidebar h3 { padding: 0 16px 12px; font-size: 14px; color: var(--text-light); border-bottom: 1px solid var(--border); margin-bottom: 8px; }

.products-content { flex: 1; }
.product-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.loading-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.empty { text-align: center; padding: 60px 0; color: var(--text-light); }
.empty-icon { font-size: 48px; display: block; margin-bottom: 12px; }
.pagination { display: flex; justify-content: center; margin-top: 32px; }

@media (max-width: 1024px) {
  .product-grid, .loading-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .sidebar { display: none; }
  .search-box { width: 100%; }
  .product-grid, .loading-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
