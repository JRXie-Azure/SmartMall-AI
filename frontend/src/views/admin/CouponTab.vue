<template>
  <div>
    <div class="card-header">
      <el-select :model-value="couponFilterActive" @update:model-value="$emit('update:couponFilterActive', $event)" placeholder="全部状态" size="small" clearable style="width:120px" @change="$emit('loadCoupons')">
        <el-option label="启用中" :value="true" />
        <el-option label="已禁用" :value="false" />
      </el-select>
      <el-button type="primary" size="small" @click="$emit('openCouponEdit', null)">+ 创建优惠券</el-button>
    </div>

    <el-table :data="coupons" stripe style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="code" label="优惠码" width="120" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column label="优惠" width="120">
        <template #default="{row}">
          <span v-if="row.discount_type === 'fixed'">减 ¥{{ row.discount_value }}</span>
          <span v-else>{{ row.discount_value }}% 折扣</span>
        </template>
      </el-table-column>
      <el-table-column prop="min_order_amount" label="最低消费" width="100">
        <template #default="{row}">¥{{ row.min_order_amount }}</template>
      </el-table-column>
      <el-table-column prop="used_count" label="已使用" width="80" />
      <el-table-column prop="total_limit" label="总量" width="80">
        <template #default="{row}">{{ row.total_limit || '不限' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{row}">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="$emit('openCouponEdit', row)">编辑</el-button>
          <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="$emit('toggleCoupon', row.id)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="couponPage"
        :page-size="couponPageSize"
        :total="couponTotal"
        :page-sizes="[10,20,50]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update:couponPage', $event)"
        @update:page-size="$emit('update:couponPageSize', $event)"
        @change="$emit('pageChange')"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  coupons: { type: Array, default: () => [] },
  couponTotal: { type: Number, default: 0 },
  couponFilterActive: { type: [Boolean, String], default: '' },
  couponPage: { type: Number, default: 1 },
  couponPageSize: { type: Number, default: 20 },
})

defineEmits([
  'update:couponFilterActive', 'loadCoupons',
  'openCouponEdit', 'toggleCoupon',
  'update:couponPage', 'update:couponPageSize', 'pageChange',
])
</script>
