<template>
  <el-form :model="settingsForm" label-width="120px" style="max-width:600px">
    <h3 style="font-size:14px;margin:16px 0 12px">网站信息</h3>
    <el-form-item label="网站名称">
      <el-input v-model="settingsForm.site_name" placeholder="SmartMall AI" />
    </el-form-item>
    <el-form-item label="网站Logo">
      <el-input v-model="settingsForm.site_logo" placeholder="图片URL" />
    </el-form-item>
    <el-form-item label="客服电话">
      <el-input v-model="settingsForm.service_phone" placeholder="400-xxx-xxxx" />
    </el-form-item>
    <el-form-item label="客服邮箱">
      <el-input v-model="settingsForm.service_email" placeholder="support@example.com" />
    </el-form-item>

    <h3 style="font-size:14px;margin:16px 0 12px">支付配置</h3>
    <el-form-item label="微信支付">
      <el-switch v-model="settingsForm.pay_wechat" />
    </el-form-item>
    <el-form-item label="支付宝">
      <el-switch v-model="settingsForm.pay_alipay" />
    </el-form-item>
    <el-form-item label="货到付款">
      <el-switch v-model="settingsForm.pay_cod" />
    </el-form-item>

    <h3 style="font-size:14px;margin:16px 0 12px">运费规则</h3>
    <el-form-item label="默认运费">
      <el-input-number v-model="settingsForm.shipping_fee" :min="0" :step="0.01" :precision="2" style="width:200px" />
      <span style="margin-left:8px">元</span>
    </el-form-item>
    <el-form-item label="包邮门槛">
      <el-input-number v-model="settingsForm.free_shipping_threshold" :min="0" :step="0.01" :precision="2" style="width:200px" />
      <span style="margin-left:8px">元（0表示不包邮）</span>
    </el-form-item>

    <h3 style="font-size:14px;margin:16px 0 12px">通知设置</h3>
    <el-form-item label="订单通知">
      <el-switch v-model="settingsForm.notify_order" />
    </el-form-item>
    <el-form-item label="新用户注册">
      <el-switch v-model="settingsForm.notify_register" />
    </el-form-item>
    <el-form-item label="低库存提醒">
      <el-switch v-model="settingsForm.notify_low_stock" />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" @click="$emit('saveSettings')" :loading="settingsSaving">保存设置</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
defineProps({
  settingsForm: { type: Object, required: true },
  settingsSaving: { type: Boolean, default: false },
})

defineEmits(['saveSettings'])
</script>
