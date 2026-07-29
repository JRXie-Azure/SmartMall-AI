<template>
  <header class="navbar" :class="{ scrolled }">
    <div class="nav-inner container">
      <router-link to="/" class="logo">
        <span class="logo-icon">🛒</span>
        <span class="logo-text">SmartMall<span class="logo-ai">AI</span></span>
      </router-link>

      <nav class="nav-links">
        <router-link to="/">首页</router-link>
        <router-link to="/products">全部商品</router-link>
        <router-link to="/products?sort=sales">AI推荐</router-link>
        <router-link to="/products?sort=newest">新品上市</router-link>
        <router-link to="/products?keyword=特惠">限时特惠</router-link>
        <router-link to="/ai-chat">AI 助手</router-link>
        <router-link v-if="auth.isAdmin" to="/admin">管理后台</router-link>
      </nav>

      <div class="nav-search">
        <el-autocomplete
          v-model="searchKeyword"
          :fetch-suggestions="fetchSuggestions"
          placeholder="搜索商品..."
          clearable
          @select="handleSearchSelect"
          @keyup.enter="handleSearch"
          style="width: 220px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
          <template #default="{ item }">
            <div class="suggest-item">
              <span class="suggest-name">{{ item.value }}</span>
              <el-tag v-if="item.type === 'brand'" size="small" type="info">品牌</el-tag>
              <el-tag v-else-if="item.type === 'hot'" size="small" type="warning">热搜</el-tag>
            </div>
          </template>
        </el-autocomplete>
      </div>

      <div class="nav-actions">
        <router-link to="/cart" class="cart-btn">
          <el-badge :value="cart.totalCount" :hidden="cart.totalCount === 0" :max="99">
            <el-icon :size="22"><ShoppingCart /></el-icon>
          </el-badge>
        </router-link>

        <template v-if="auth.isLoggedIn">
          <el-dropdown trigger="click">
            <span class="user-btn">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ auth.user?.username || '用户' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/user')">个人中心</el-dropdown-item>
                <el-dropdown-item @click="$router.push('/orders')">我的订单</el-dropdown-item>
                <el-dropdown-item v-if="auth.isAdmin" @click="$router.push('/admin')">管理后台</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <router-link to="/login" class="login-link">登录</router-link>
          <router-link to="/register"><el-button type="primary" size="small">注册</el-button></router-link>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'
import { ShoppingCart, Search } from '@element-plus/icons-vue'
import { searchAPI } from '../api'

const router = useRouter()
const auth = useAuthStore()
const cart = useCartStore()
const scrolled = ref(false)
const searchKeyword = ref('')

async function fetchSuggestions(queryString, cb) {
  if (!queryString || queryString.trim().length < 1) {
    // Show hot searches when empty
    try {
      const res = await searchAPI.hot()
      const hotItems = (res.data || []).slice(0, 5).map(h => ({
        value: h.keyword,
        type: 'hot',
      }))
      cb(hotItems)
    } catch {
      cb([])
    }
    return
  }
  try {
    const res = await searchAPI.suggestions(queryString.trim())
    const data = res.data || {}
    const items = []
    ;(data.products || []).forEach(p => items.push({ value: p, type: 'product' }))
    ;(data.brands || []).forEach(b => items.push({ value: b, type: 'brand' }))
    ;(data.hot_keywords || []).forEach(k => items.push({ value: k, type: 'hot' }))
    cb(items.slice(0, 8))
  } catch {
    cb([])
  }
}

function handleSearchSelect(item) {
  if (item.value) {
    router.push({ path: '/products', query: { keyword: item.value } })
  }
}

function handleSearch() {
  if (searchKeyword.value.trim()) {
    router.push({ path: '/products', query: { keyword: searchKeyword.value.trim() } })
  }
}

function handleScroll() { scrolled.value = window.scrollY > 10 }
onMounted(() => {
  window.addEventListener('scroll', handleScroll)
  if (auth.isLoggedIn) cart.fetchCart()
})
onUnmounted(() => window.removeEventListener('scroll', handleScroll))

function handleLogout() {
  auth.logout()
  cart.items = []
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid transparent;
  transition: all 0.3s;
}
.navbar.scrolled {
  border-bottom-color: var(--border);
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 20px;
}
.logo-icon { font-size: 26px; }
.logo-ai {
  background: linear-gradient(135deg, #6C5CE7, #FF6B6B);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nav-search { flex: 1; max-width: 300px; display: flex; justify-content: center; }
.suggest-item { display: flex; align-items: center; justify-content: space-between; }
.suggest-name { font-size: 13px; }
@media (max-width: 768px) {
  .nav-search { display: none; }
}
.nav-links { display: flex; gap: 28px; }
.nav-links a {
  font-size: 14px;
  color: var(--text-light);
  transition: color 0.2s;
  position: relative;
}
.nav-links a:hover,
.nav-links a.router-link-active { color: var(--primary); }
.nav-links a.router-link-active::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  background: var(--primary);
  border-radius: 2px;
}
.nav-actions { display: flex; align-items: center; gap: 16px; }
.cart-btn { color: var(--text-light); padding: 4px; }
.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}
.username { max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.login-link {
  font-size: 14px;
  color: var(--primary);
  font-weight: 500;
}

@media (max-width: 768px) {
  .nav-links { display: none; }
  .username { display: none; }
}
</style>
