<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">登录 SmartMall-AI</h1>
      <p class="auth-sub">欢迎回来，AI 购物体验从这里开始</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" native-type="submit" :loading="auth.loading" style="width:100%;margin-top:8px">
          登录
        </el-button>
      </el-form>

      <div class="auth-footer">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
      </div>


    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const cart = useCartStore()
const formRef = ref()

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    const ok = await auth.login(form.username, form.password)
    if (ok) {
      ElMessage.success('登录成功！')
      cart.fetchCart()
      router.push(route.query.redirect || '/')
    }
  })
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
