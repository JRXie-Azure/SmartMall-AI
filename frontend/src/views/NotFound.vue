<template>
  <div class="not-found">
    <h1>404</h1>
    <p>页面不存在</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<script setup>
</script>

<style scoped>
.not-found {
  text-align: center;
  padding: 80px 20px;
}
.not-found h1 {
  font-size: 72px;
  color: var(--primary);
  margin-bottom: 16px;
}
.not-found p {
  color: var(--text-light);
  margin-bottom: 24px;
  font-size: 16px;
}
</style>
