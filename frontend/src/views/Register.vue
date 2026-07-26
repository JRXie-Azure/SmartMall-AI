<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">创建账号</h1>
      <p class="auth-sub">加入 SmartMall-AI，体验 AI 智能购物</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" size="large" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少6位密码" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" native-type="submit" :loading="auth.loading" style="width:100%;margin-top:8px">
          注册
        </el-button>
      </el-form>

      <div class="auth-footer">
        <span>已有账号？</span>
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ email: '', username: '', password: '' })
const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度3-20位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

async function handleRegister() {
  const ok = await auth.register(form.email, form.username, form.password)
  if (ok) {
    ElMessage.success('注册成功，请登录！')
    router.push('/login')
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  background: linear-gradient(135deg, #F8F9FA 0%, #E8EAF6 100%);
}
.auth-card {
  width: 420px;
  padding: 40px;
}
.auth-title { font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 8px; }
.auth-sub { font-size: 14px; color: var(--text-light); text-align: center; margin-bottom: 32px; }
.auth-footer { text-align: center; margin-top: 20px; font-size: 13px; color: var(--text-light); }
.auth-footer a { color: var(--primary); font-weight: 600; margin-left: 4px; }
</style>
