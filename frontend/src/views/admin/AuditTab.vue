<template>
  <div>
    <div class="filter-bar" style="margin-bottom:12px">
      <el-button size="small" @click="$emit('loadAuditProducts')">刷新</el-button>
    </div>

    <el-table :data="auditProducts" stripe style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="图片" width="70">
        <template #default="{row}">
          <img :src="row.image" style="width:44px;height:44px;object-fit:cover;border-radius:4px" />
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="brand" label="品牌" width="100" />
      <el-table-column label="价格" width="100">
        <template #default="{row}">
          <span style="color:#e74c3c;font-weight:600">¥{{ row.price }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stock" label="库存" width="80" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{row}">
          <el-button size="small" type="success" @click="$emit('auditProduct', row.id, 'approved')">通过</el-button>
          <el-button size="small" type="danger" @click="$emit('auditProduct', row.id, 'rejected')">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="auditPage"
        :page-size="auditPageSize"
        :total="auditTotal"
        :page-sizes="[10,20,50]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update:auditPage', $event)"
        @update:page-size="$emit('update:auditPageSize', $event)"
        @change="$emit('pageChange')"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  auditProducts: { type: Array, default: () => [] },
  auditTotal: { type: Number, default: 0 },
  auditPage: { type: Number, default: 1 },
  auditPageSize: { type: Number, default: 20 },
})

defineEmits([
  'loadAuditProducts', 'auditProduct',
  'update:auditPage', 'update:auditPageSize', 'pageChange',
])
</script>
