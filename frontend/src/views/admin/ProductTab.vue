<template>
  <div>
    <div class="card-header">
      <div class="filter-bar">
        <el-input :model-value="filterKeyword" @update:model-value="$emit('update:filterKeyword', $event)" placeholder="搜索商品名称" style="width:200px" size="small" clearable @keyup.enter="$emit('search')" />
        <el-select :model-value="filterStatus" @update:model-value="$emit('update:filterStatus', $event)" placeholder="全部状态" size="small" clearable style="width:120px">
          <el-option label="上架" value="active" />
          <el-option label="下架" value="inactive" />
        </el-select>
        <el-select :model-value="filterAudit" @update:model-value="$emit('update:filterAudit', $event)" placeholder="审核状态" size="small" clearable style="width:120px">
          <el-option label="已通过" value="approved" />
          <el-option label="待审核" value="pending" />
          <el-option label="已拒绝" value="rejected" />
        </el-select>
        <el-button size="small" @click="$emit('search')">搜索</el-button>
        <el-button size="small" type="warning" @click="$emit('showLowStock')">库存预警</el-button>
      </div>
      <el-button type="primary" size="small" @click="$emit('openEdit', null)">+ 添加商品</el-button>
    </div>

    <div v-if="selectedProductIds.length" class="batch-bar">
      <span>已选 {{ selectedProductIds.length }} 项</span>
      <el-button size="small" @click="$emit('batchAction', 'activate')">批量上架</el-button>
      <el-button size="small" @click="$emit('batchAction', 'deactivate')">批量下架</el-button>
      <el-button size="small" type="danger" @click="$emit('batchAction', 'delete')">批量删除</el-button>
    </div>

    <el-table :data="products" stripe style="width:100%" @selection-change="$emit('selectionChange', $event)">
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="图片" width="70">
        <template #default="{row}">
          <img :src="row.image" style="width:44px;height:44px;object-fit:cover;border-radius:4px" />
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="brand" label="品牌" width="90" />
      <el-table-column label="价格" width="100">
        <template #default="{row}">
          <span style="color:#e74c3c;font-weight:600">¥{{ row.price }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stock" label="库存" width="70">
        <template #default="{row}">
          <span :class="{ 'text-danger': row.stock <= 10 }">{{ row.stock }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sales" label="销量" width="70" />
      <el-table-column label="标签" width="140">
        <template #default="{row}">
          <el-tag v-if="row.is_recommend" size="small" type="warning" style="margin-right:4px">推荐</el-tag>
          <el-tag v-if="row.is_new" size="small" type="success" style="margin-right:4px">新品</el-tag>
          <el-tag v-if="row.is_sale" size="small" type="danger">特惠</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{row}">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '上架' : '下架' }}</el-tag>
          <el-tag v-if="row.audit_status === 'pending'" size="small" type="warning" style="margin-left:4px">待审</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{row}">
          <el-button size="small" @click="$emit('openEdit', row)">编辑</el-button>
          <el-button size="small" type="danger" @click="$emit('deleteProduct', row.id)">下架</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        :page-sizes="[10,20,50]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update:page', $event)"
        @update:page-size="$emit('update:pageSize', $event)"
        @change="$emit('pageChange')"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  products: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
  filterKeyword: { type: String, default: '' },
  filterStatus: { type: String, default: '' },
  filterAudit: { type: String, default: '' },
  selectedProductIds: { type: Array, default: () => [] },
  page: { type: Number, default: 1 },
  pageSize: { type: Number, default: 20 },
})

defineEmits([
  'update:filterKeyword', 'update:filterStatus', 'update:filterAudit',
  'search', 'showLowStock', 'openEdit', 'deleteProduct',
  'selectionChange', 'batchAction',
  'update:page', 'update:pageSize', 'pageChange',
])
</script>
