<template>
  <div class="user-page container">
    <h1 class="page-title">个人中心</h1>

    <div class="user-layout">
      <!-- 左侧用户卡片 -->
      <div class="user-card card">
        <el-avatar :size="64" icon="UserFilled" />
        <h2>{{ auth.user?.username || '用户' }}</h2>
        <p>{{ auth.user?.email }}</p>
        <el-tag :type="auth.isAdmin ? 'danger' : 'success'">{{ auth.isAdmin ? '管理员' : '普通用户' }}</el-tag>
        <div class="quick-links">
          <router-link to="/orders" class="action-item">
            <span class="action-icon">📦</span><span>我的订单</span>
          </router-link>
          <router-link to="/cart" class="action-item">
            <span class="action-icon">🛒</span><span>购物车</span>
          </router-link>
          <router-link to="/ai-chat" class="action-item">
            <span class="action-icon">🤖</span><span>AI助手</span>
          </router-link>
          <router-link v-if="auth.isAdmin" to="/admin" class="action-item">
            <span class="action-icon">⚙️</span><span>管理后台</span>
          </router-link>
        </div>
      </div>

      <!-- 右侧 Tab 内容 -->
      <div class="user-content card">
        <el-tabs v-model="activeTab">
          <!-- 收藏列表 -->
          <el-tab-pane label="我的收藏" name="favorites">
            <div v-if="favLoading" class="loading-wrap"><el-skeleton :rows="3" animated /></div>
            <div v-else-if="favorites.length === 0" class="empty-tab">暂无收藏</div>
            <div v-else class="fav-list">
              <div v-for="p in favorites" :key="p.id" class="fav-item">
                <router-link :to="`/product/${p.id}`" class="fav-img">
                  <img :src="p.image" :alt="p.name" />
                </router-link>
                <div class="fav-info">
                  <router-link :to="`/product/${p.id}`" class="fav-name">{{ p.name }}</router-link>
                  <span class="fav-price">¥{{ p.price }}</span>
                </div>
                <el-button type="danger" link size="small" @click="toggleFav(p.id)">取消收藏</el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- 订单统计 -->
          <el-tab-pane label="订单概览" name="orders">
            <div v-if="orderStats" class="order-stats-grid">
              <div class="stat-box"><span class="stat-val">{{ orderStats.total || 0 }}</span><span class="stat-lbl">总订单</span></div>
              <div class="stat-box"><span class="stat-val">{{ orderStats.pending || 0 }}</span><span class="stat-lbl">待付款</span></div>
              <div class="stat-box"><span class="stat-val">{{ orderStats.paid || 0 }}</span><span class="stat-lbl">已付款</span></div>
              <div class="stat-box"><span class="stat-val">{{ orderStats.shipped || 0 }}</span><span class="stat-lbl">已发货</span></div>
              <div class="stat-box"><span class="stat-val">{{ orderStats.completed || 0 }}</span><span class="stat-lbl">已完成</span></div>
              <div class="stat-box"><span class="stat-val">¥{{ (orderStats.total_amount || 0).toFixed(0) }}</span><span class="stat-lbl">总消费</span></div>
            </div>
            <router-link to="/orders" style="display:block;text-align:center;margin-top:16px">
              <el-button type="primary" plain>查看全部订单</el-button>
            </router-link>
          </el-tab-pane>

          <!-- 修改密码 -->
          <el-tab-pane label="修改密码" name="password">
            <div class="password-form">
              <el-form label-width="80px" style="max-width:400px">
                <el-form-item label="新密码">
                  <el-input v-model="pwdForm.password" type="password" show-password placeholder="至少8位" />
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input v-model="pwdForm.confirmPassword" type="password" show-password />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="changePassword" :loading="pwdLoading">确认修改</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { productsAPI, ordersAPI, authAPI } from '../api'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const activeTab = ref('favorites')

// 收藏
const favorites = ref([])
const favLoading = ref(false)

// 订单统计
const orderStats = ref(null)

// 修改密码
const pwdForm = ref({ password: '', confirmPassword: '' })
const pwdLoading = ref(false)

async function loadFavorites() {
  favLoading.value = true
  try {
    const res = await productsAPI.getFavorites()
    favorites.value = res.data || []
  } catch { favorites.value = [] }
  favLoading.value = false
}

async function toggleFav(productId) {
  try {
    await productsAPI.removeFavorite(productId)  // toggle
    favorites.value = favorites.value.filter(p => p.id !== productId)
    ElMessage.success('已取消收藏')
  } catch { ElMessage.error('操作失败') }
}

async function loadOrderStats() {
  try {
    const res = await ordersAPI.getStats()
    orderStats.value = res.data
  } catch {}
}

async function changePassword() {
  if (pwdForm.value.password.length < 8) { ElMessage.warning('密码至少8位'); return }
  if (pwdForm.value.password !== pwdForm.value.confirmPassword) { ElMessage.error('两次密码不一致'); return }
  pwdLoading.value = true
  try {
    await authAPI.updateMe({ password: pwdForm.value.password })
    ElMessage.success('密码修改成功')
    pwdForm.value = { password: '', confirmPassword: '' }
  } catch { ElMessage.error('密码修改失败') }
  pwdLoading.value = false
}

onMounted(() => {
  loadFavorites()
  loadOrderStats()
})
</script>

<style scoped>
.user-page { padding: 40px 0 60px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.user-layout { display: flex; gap: 24px; }
.user-card {
  width: 280px;
  text-align: center;
  padding: 32px;
}
.user-card h2 { font-size: 18px; margin-top: 12px; margin-bottom: 4px; }
.user-card p { font-size: 13px; color: var(--text-light); margin-bottom: 12px; }

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  transition: all 0.2s;
  font-size: 14px;
}
.action-item:hover { border-color: var(--primary); background: #F8F0FF; }
.action-icon { font-size: 28px; }

.quick-links { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 20px; }
.user-content { flex: 1; padding: 24px; min-height: 400px; }
.loading-wrap, .empty-tab { padding: 40px; text-align: center; color: var(--text-light); }
.fav-list { display: flex; flex-direction: column; gap: 12px; }
.fav-item { display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid var(--border); border-radius: 8px; }
.fav-img { width: 60px; height: 60px; border-radius: 6px; overflow: hidden; flex-shrink: 0; }
.fav-img img { width: 100%; height: 100%; object-fit: cover; }
.fav-info { flex: 1; }
.fav-name { font-size: 14px; font-weight: 600; display: block; margin-bottom: 4px; }
.fav-price { font-size: 16px; font-weight: 700; color: var(--accent); }
.order-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-box { text-align: center; padding: 16px; border: 1px solid var(--border); border-radius: 8px; }
.stat-val { font-size: 24px; font-weight: 700; color: var(--primary); display: block; }
.stat-lbl { font-size: 12px; color: var(--text-light); }
.password-form { max-width: 400px; }

@media (max-width: 768px) {
  .user-layout { flex-direction: column; }
  .user-card { width: 100%; }
  .quick-links { grid-template-columns: 1fr 1fr; }
}
</style>
