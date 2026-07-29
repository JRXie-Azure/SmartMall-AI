<template>
  <div>
    <el-tabs :model-value="marketingSubTab" @update:model-value="$emit('update:marketingSubTab', $event)" type="card">
      <el-tab-pane label="营销活动" name="campaigns">
        <div class="card-header">
          <el-select :model-value="campaignFilterActive" @update:model-value="$emit('update:campaignFilterActive', $event)" placeholder="全部状态" size="small" clearable style="width:120px" @change="$emit('loadCampaigns')">
            <el-option label="进行中" :value="true" />
            <el-option label="已停用" :value="false" />
          </el-select>
          <el-button type="primary" size="small" @click="$emit('openCampaignEdit', null)">+ 创建活动</el-button>
        </div>
        <el-table :data="campaigns" stripe style="width:100%">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="活动名称" min-width="140" />
          <el-table-column label="类型" width="100">
            <template #default="{row}">
              <el-tag size="small">{{ campaignTypeLabel(row.campaign_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="优惠" width="120">
            <template #default="{row}">
              <span v-if="row.campaign_type === 'full_reduction'">满{{ row.min_order_amount }}减{{ row.discount_value }}</span>
              <span v-else-if="row.campaign_type === 'discount'">减 ¥{{ row.discount_value }}</span>
              <span v-else>{{ row.discount_value }}% 折扣</span>
            </template>
          </el-table-column>
          <el-table-column label="时间范围" min-width="200">
            <template #default="{row}">
              {{ formatDate(row.start_time) }} ~ {{ formatDate(row.end_time) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{row}">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{row}">
              <el-button size="small" @click="$emit('openCampaignEdit', row)">编辑</el-button>
              <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="$emit('toggleCampaign', row.id)">
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-bar">
          <el-pagination
            :current-page="campaignPage"
            :page-size="campaignPageSize"
            :total="campaignTotal"
            :page-sizes="[10,20,50]"
            layout="total, sizes, prev, pager, next"
            @update:current-page="$emit('update:campaignPage', $event)"
            @update:page-size="$emit('update:campaignPageSize', $event)"
            @change="$emit('campaignPageChange')"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="Banner 轮播" name="banners">
        <div class="card-header">
          <span />
          <el-button type="primary" size="small" @click="$emit('openBannerEdit', null)">+ 添加 Banner</el-button>
        </div>
        <el-table :data="banners" stripe style="width:100%">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column label="图片" width="100">
            <template #default="{row}">
              <img :src="row.image" style="width:60px;height:40px;object-fit:cover;border-radius:4px" />
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" min-width="120" />
          <el-table-column prop="link" label="链接" min-width="160" show-overflow-tooltip />
          <el-table-column prop="sort_order" label="排序" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{row}">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '显示' : '隐藏' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{row}">
              <el-button size="small" @click="$emit('openBannerEdit', row)">编辑</el-button>
              <el-button size="small" type="danger" @click="$emit('deleteBanner', row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
function campaignTypeLabel(type) {
  const map = { discount: '固定减免', flash_sale: '限时折扣', full_reduction: '满减' }
  return map[type] || type
}

function formatDate(d) {
  if (!d) return '-'
  return d.slice(0, 16).replace('T', ' ')
}

defineProps({
  marketingSubTab: { type: String, default: 'campaigns' },
  campaigns: { type: Array, default: () => [] },
  campaignTotal: { type: Number, default: 0 },
  campaignFilterActive: { type: [Boolean, String], default: '' },
  campaignPage: { type: Number, default: 1 },
  campaignPageSize: { type: Number, default: 20 },
  banners: { type: Array, default: () => [] },
})

defineEmits([
  'update:marketingSubTab',
  'update:campaignFilterActive', 'loadCampaigns',
  'openCampaignEdit', 'toggleCampaign',
  'update:campaignPage', 'update:campaignPageSize', 'campaignPageChange',
  'openBannerEdit', 'deleteBanner',
])
</script>
