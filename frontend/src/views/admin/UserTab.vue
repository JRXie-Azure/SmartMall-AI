<template>
  <div>
    <div class="filter-bar" style="margin-bottom:12px">
      <el-select :model-value="userRoleFilter" @update:model-value="$emit('update:userRoleFilter', $event)" placeholder="全部角色" size="small" clearable style="width:120px" @change="$emit('loadUsers')">
        <el-option label="普通用户" value="user" />
        <el-option label="商家" value="merchant" />
        <el-option label="管理员" value="admin" />
      </el-select>
      <el-button size="small" @click="$emit('loadUsers')">刷新</el-button>
    </div>

    <el-table :data="users" stripe style="width:100%">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="email" label="邮箱" min-width="160" />
      <el-table-column prop="phone" label="手机号" width="120" />
      <el-table-column label="角色" width="100">
        <template #default="{row}">
          <el-select :model-value="row.role" size="small" style="width:90px" @change="(val) => $emit('changeUserRole', row.id, val)">
            <el-option label="用户" value="user" />
            <el-option label="商家" value="merchant" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{row}">
          <el-switch
            :model-value="row.is_active"
            active-text="正常"
            inactive-text="禁用"
            inline-prompt
            @change="$emit('toggleUser', row.id)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="160" />
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="userPage"
        :page-size="userPageSize"
        :total="userTotal"
        :page-sizes="[10,20,50]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update:userPage', $event)"
        @update:page-size="$emit('update:userPageSize', $event)"
        @change="$emit('pageChange')"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  users: { type: Array, default: () => [] },
  userTotal: { type: Number, default: 0 },
  userRoleFilter: { type: String, default: '' },
  userPage: { type: Number, default: 1 },
  userPageSize: { type: Number, default: 20 },
})

defineEmits([
  'update:userRoleFilter', 'loadUsers',
  'toggleUser', 'changeUserRole',
  'update:userPage', 'update:userPageSize', 'pageChange',
])
</script>
