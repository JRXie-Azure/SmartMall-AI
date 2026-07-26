<template>
  <div class="user-page container">
    <h1 class="page-title">个人中心</h1>

    <div class="user-layout">
      <div class="user-card card">
        <el-avatar :size="64" icon="UserFilled" />
        <h2>{{ auth.user?.username || '用户' }}</h2>
        <p>{{ auth.user?.email }}</p>
        <el-tag :type="auth.isAdmin ? 'danger' : 'success'">{{ auth.isAdmin ? '管理员' : '普通用户' }}</el-tag>
      </div>

      <div class="user-actions card">
        <h3>快捷操作</h3>
        <div class="action-grid">
          <router-link to="/orders" class="action-item">
            <span class="action-icon">📦</span>
            <span>我的订单</span>
          </router-link>
          <router-link to="/cart" class="action-item">
            <span class="action-icon">🛒</span>
            <span>购物车</span>
          </router-link>
          <router-link to="/ai-chat" class="action-item">
            <span class="action-icon">🤖</span>
            <span>AI 助手</span>
          </router-link>
          <router-link v-if="auth.isAdmin" to="/admin" class="action-item">
            <span class="action-icon">⚙️</span>
            <span>管理后台</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
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

.user-actions { flex: 1; padding: 24px; }
.user-actions h3 { font-size: 16px; margin-bottom: 16px; }
.action-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
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

@media (max-width: 768px) {
  .user-layout { flex-direction: column; }
  .user-card { width: 100%; }
  .action-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
