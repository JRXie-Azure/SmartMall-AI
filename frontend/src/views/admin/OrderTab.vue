<template>
  <div>
    <div class="filter-bar" style="margin-bottom:12px">
      <el-select :model-value="orderStatusFilter" @update:model-value="$emit('update:orderStatusFilter', $event)" placeholder="全部状态" size="small" clearable style="width:140px" @change="$emit('loadOrders')">
        <el-option label="待付款" value="pending" />
        <el-option label="已付款" value="paid" />
        <el-option label="已发货" value="shipped" />
        <el-option label="已完成" value="completed" />
        <el-option label="已取消" value="cancelled" />
        <el-option label="已退款" value="refunded" />
      </el-select>
      <el-button size="small" @click="$emit('loadOrders')">刷新</el-button>
    </div>

    <el-table :data="orders" stripe style="width:100%">
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column label="商品" min-width="160">
        <template #default="{row}">
          <div v-for="item in row.items" :key="item.product_name" class="order-item-line">
            {{ item.product_name }} x{{ item.quantity }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="100">
        <template #default="{row}">
          <span style="color:#e74c3c;font-weight:600">¥{{ row.total_amount }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{row}">
          <el-tag :type="orderStatusType(row.status)" size="small">{{ orderStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{row}">
          <el-button v-if="row.status === 'paid'" size="small" type="primary" @click="$emit('openShip', row)">发货</el-button>
          <el-button v-else size="small" @click="$emit('openOrderStatus', row)">改状态</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="orderPage"
        :page-size="orderPageSize"
        :total="orderTotal"
        :page-sizes="[10,20,50]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update:orderPage', $event)"
        @update:page-size="$emit('update:orderPageSize', $event)"
        @change="$emit('pageChange')"
      />
    </div>
  </div>
</template>

<script setup>
const orderStatusMap = {
  pending: { label: '待付款', type: 'warning' },
  paid: { label: '已付款', type: 'primary' },
  shipped: { label: '已发货', type: 'success' },
  completed: { label: '已完成', type: 'success' },
  cancelled: { label: '已取消', type: 'info' },
  refunded: { label: '已退款', type: 'danger' },
}

function orderStatusLabel(status) {
  return orderStatusMap[status]?.label || status
}

function orderStatusType(status) {
  return orderStatusMap[status]?.type || 'info'
}

defineProps({
  orders: { type: Array, default: () => [] },
  orderTotal: { type: Number, default: 0 },
  orderStatusFilter: { type: String, default: '' },
  orderPage: { type: Number, default: 1 },
  orderPageSize: { type: Number, default: 20 },
})

defineEmits([
  'update:orderStatusFilter', 'loadOrders',
  'openShip', 'openOrderStatus',
  'update:orderPage', 'update:orderPageSize', 'pageChange',
])
</script>
