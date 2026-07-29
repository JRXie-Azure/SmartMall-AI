<template>
  <div class="admin-page container">
    <h1 class="page-title">管理后台</h1>
    <el-tabs v-model="activeTab" type="border-card" class="admin-tabs">
      <el-tab-pane label="数据概览" name="overview">
        <OverviewTab :stats-cards="statsCards" :alerts="alerts" :sales-option="salesOption" :category-option="categoryOption" />
      </el-tab-pane>
      <el-tab-pane label="商品管理" name="products">
        <ProductTab :products="products" :total="total" v-model:filter-keyword="filterKeyword" v-model:filter-status="filterStatus" v-model:filter-audit="filterAudit" :selected-product-ids="selectedProductIds" v-model:page="page" v-model:page-size="pageSize" @search="loadProducts" @show-low-stock="showLowStock" @open-edit="openEdit" @delete-product="deleteProduct" @selection-change="handleSelectionChange" @batch-action="batchAction" @page-change="loadProducts" />
      </el-tab-pane>
      <el-tab-pane label="订单管理" name="orders">
        <OrderTab :orders="orders" :order-total="orderTotal" v-model:order-status-filter="orderStatusFilter" v-model:order-page="orderPage" v-model:order-page-size="orderPageSize" @load-orders="loadOrders" @open-ship="openShip" @open-order-status="openOrderStatus" @page-change="loadOrders" />
      </el-tab-pane>
      <el-tab-pane label="用户管理" name="users">
        <UserTab :users="users" :user-total="userTotal" v-model:user-role-filter="userRoleFilter" v-model:user-page="userPage" v-model:user-page-size="userPageSize" @load-users="loadUsers" @toggle-user="toggleUser" @change-user-role="changeUserRole" @page-change="loadUsers" />
      </el-tab-pane>
      <el-tab-pane label="商品审核" name="audit">
        <AuditTab :audit-products="auditProducts" :audit-total="auditTotal" v-model:audit-page="auditPage" v-model:audit-page-size="auditPageSize" @load-audit-products="loadAuditProducts" @audit-product="auditProduct" @page-change="loadAuditProducts" />
      </el-tab-pane>
      <el-tab-pane label="优惠券" name="coupons">
        <CouponTab :coupons="coupons" :coupon-total="couponTotal" v-model:coupon-filter-active="couponFilterActive" v-model:coupon-page="couponPage" v-model:coupon-page-size="couponPageSize" @load-coupons="loadCoupons" @open-coupon-edit="openCouponEdit" @toggle-coupon="toggleCoupon" @page-change="loadCoupons" />
      </el-tab-pane>
      <el-tab-pane label="AI 分析" name="ai">
        <AiTab :ai-data="aiData" :ai-forecast-option="aiForecastOption" />
      </el-tab-pane>
      <el-tab-pane label="营销管理" name="marketing">
        <MarketingTab v-model:marketing-sub-tab="marketingSubTab" :campaigns="campaigns" :campaign-total="campaignTotal" v-model:campaign-filter-active="campaignFilterActive" v-model:campaign-page="campaignPage" v-model:campaign-page-size="campaignPageSize" :banners="banners" @load-campaigns="loadCampaigns" @open-campaign-edit="openCampaignEdit" @toggle-campaign="toggleCampaign" @campaign-page-change="loadCampaigns" @open-banner-edit="openBannerEdit" @delete-banner="deleteBanner" />
      </el-tab-pane>
      <el-tab-pane label="系统设置" name="settings">
        <SettingsTab :settings-form="settingsForm" :settings-saving="settingsSaving" @save-settings="saveSettings" />
      </el-tab-pane>
    </el-tabs>
    <!-- 商品编辑弹窗 -->
    <el-dialog v-model="editVisible" :title="editingProduct?.id ? '编辑商品' : '添加商品'" width="620px" destroy-on-close>
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="商品图片">
          <div class="img-upload-wrap">
            <img v-if="editForm.image" :src="editForm.image" class="preview-img" />
            <div v-else class="img-placeholder">暂无图片</div>
            <el-upload :http-request="customUpload" :show-file-list="false" accept="image/*" class="upload-btn">
              <el-button size="small" type="primary" :loading="uploading">{{ editForm.image ? '更换图片' : '上传图片' }}</el-button>
            </el-upload>
            <el-input v-model="editForm.image" placeholder="或输入图片URL" size="small" style="margin-top:8px" />
          </div>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="商品名称" required>
              <el-input v-model="editForm.name" placeholder="如: Nike Air Max 270" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="品牌">
              <el-input v-model="editForm.brand" placeholder="如: Nike" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="商品详细描述..." />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="售价" required>
              <el-input-number v-model="editForm.price" :min="0" :step="0.01" :precision="2" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="原价">
              <el-input-number v-model="editForm.original_price" :min="0" :step="0.01" :precision="2" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="库存" required>
              <el-input-number v-model="editForm.stock" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="editForm.category_id" placeholder="选择分类" style="width:100%" clearable>
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-select v-model="editForm.tags" multiple placeholder="选择标签" style="width:100%" allow-create filterable>
                <el-option label="热销" value="热销" />
                <el-option label="限量" value="限量" />
                <el-option label="明星同款" value="明星同款" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="商品属性">
          <el-checkbox v-model="editForm.is_active">上架</el-checkbox>
          <el-checkbox v-model="editForm.is_recommend">AI推荐</el-checkbox>
          <el-checkbox v-model="editForm.is_new">新品</el-checkbox>
          <el-checkbox v-model="editForm.is_sale">限时特惠</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProduct" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
    <!-- 发货弹窗 -->
    <el-dialog v-model="shipVisible" title="订单发货" width="420px" destroy-on-close>
      <el-form :model="shipForm" label-width="100px">
        <el-form-item label="物流公司">
          <el-input v-model="shipForm.logistics_company" placeholder="如: 顺丰速运" />
        </el-form-item>
        <el-form-item label="物流单号">
          <el-input v-model="shipForm.tracking_no" placeholder="请输入物流单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmShip" :loading="shipLoading">确认发货</el-button>
      </template>
    </el-dialog>
    <!-- 订单状态修改 -->
    <el-dialog v-model="orderStatusVisible" title="修改订单状态" width="360px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="新状态">
          <el-select v-model="orderStatusForm.status" style="width:100%">
            <el-option label="待付款" value="pending" />
            <el-option label="已付款" value="paid" />
            <el-option label="已发货" value="shipped" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="已退款" value="refunded" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="orderStatusVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmOrderStatus" :loading="orderStatusLoading">确认</el-button>
      </template>
    </el-dialog>
    <!-- 优惠券编辑弹窗 -->
    <el-dialog v-model="couponVisible" :title="editingCoupon?.id ? '编辑优惠券' : '创建优惠券'" width="520px" destroy-on-close>
      <el-form :model="couponForm" label-width="100px">
        <el-form-item label="优惠码" required>
          <el-input v-model="couponForm.code" placeholder="如: SUMMER2024" :disabled="!!editingCoupon?.id" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="couponForm.name" placeholder="如: 夏季大促满减券" />
        </el-form-item>
        <el-form-item label="优惠类型">
          <el-radio-group v-model="couponForm.discount_type">
            <el-radio-button label="fixed">固定金额</el-radio-button>
            <el-radio-button label="percent">百分比</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="couponForm.discount_type === 'fixed' ? '减免金额' : '折扣比例'" required>
          <el-input-number v-model="couponForm.discount_value" :min="0.01" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="最低消费">
          <el-input-number v-model="couponForm.min_order_amount" :min="0" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="最大减免" v-if="couponForm.discount_type === 'percent'">
          <el-input-number v-model="couponForm.max_discount" :min="0" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-date-picker v-model="couponForm.valid_from" type="datetime" placeholder="选择开始时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-date-picker v-model="couponForm.valid_until" type="datetime" placeholder="选择结束时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="发放总量">
          <el-input-number v-model="couponForm.total_limit" :min="0" style="width:100%" />
          <span style="color:#999;font-size:12px">0 表示不限量</span>
        </el-form-item>
        <el-form-item label="每人限领">
          <el-input-number v-model="couponForm.per_user_limit" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="couponForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="couponVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCoupon" :loading="couponSaving">保存</el-button>
      </template>
    </el-dialog>
    <!-- 营销活动编辑弹窗 -->
    <el-dialog v-model="campaignVisible" :title="editingCampaign?.id ? '编辑活动' : '创建活动'" width="520px" destroy-on-close>
      <el-form :model="campaignForm" label-width="100px">
        <el-form-item label="活动名称" required>
          <el-input v-model="campaignForm.name" placeholder="如: 夏季大促" />
        </el-form-item>
        <el-form-item label="活动类型">
          <el-radio-group v-model="campaignForm.campaign_type">
            <el-radio-button label="discount">固定减免</el-radio-button>
            <el-radio-button label="flash_sale">限时折扣</el-radio-button>
            <el-radio-button label="full_reduction">满减</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="优惠金额/比例" required>
          <el-input-number v-model="campaignForm.discount_value" :min="0.01" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-form-item label="满减门槛" v-if="campaignForm.campaign_type === 'full_reduction'">
          <el-input-number v-model="campaignForm.min_order_amount" :min="0" :step="0.01" style="width:100%" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-date-picker v-model="campaignForm.start_time" type="datetime" placeholder="选择开始时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-date-picker v-model="campaignForm.end_time" type="datetime" placeholder="选择结束时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Banner图">
          <el-input v-model="campaignForm.banner_image" placeholder="图片URL" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="campaignForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="campaignVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCampaign" :loading="campaignSaving">保存</el-button>
      </template>
    </el-dialog>
    <!-- Banner 编辑弹窗 -->
    <el-dialog v-model="bannerVisible" :title="editingBanner?.id ? '编辑Banner' : '添加Banner'" width="420px" destroy-on-close>
      <el-form :model="bannerForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="bannerForm.title" placeholder="Banner标题" />
        </el-form-item>
        <el-form-item label="图片" required>
          <el-input v-model="bannerForm.image" placeholder="图片URL" />
        </el-form-item>
        <el-form-item label="链接">
          <el-input v-model="bannerForm.link" placeholder="跳转链接" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="bannerForm.sort_order" :min="0" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bannerVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBanner" :loading="bannerSaving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import OverviewTab from './admin/OverviewTab.vue'
import ProductTab from './admin/ProductTab.vue'
import OrderTab from './admin/OrderTab.vue'
import UserTab from './admin/UserTab.vue'
import AuditTab from './admin/AuditTab.vue'
import CouponTab from './admin/CouponTab.vue'
import AiTab from './admin/AiTab.vue'
import MarketingTab from './admin/MarketingTab.vue'
import SettingsTab from './admin/SettingsTab.vue'
import { useAdmin } from './admin/composables/useAdmin.js'

use([CanvasRenderer, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const {
  activeTab,
  statsCards, alerts, salesOption, categoryOption, loadStats,
  products, total, filterKeyword, filterStatus, filterAudit, selectedProductIds, page, pageSize,
  categories, editVisible, editingProduct, saving, uploading, editForm,
  loadProducts, loadCategories, openEdit, customUpload, saveProduct, deleteProduct,
  handleSelectionChange, batchAction, showLowStock,
  orders, orderTotal, orderStatusFilter, orderPage, orderPageSize,
  shipVisible, shipLoading, shipForm,
  orderStatusVisible, orderStatusLoading, orderStatusForm,
  loadOrders, openShip, confirmShip, openOrderStatus, confirmOrderStatus,
  users, userTotal, userRoleFilter, userPage, userPageSize,
  loadUsers, toggleUser, changeUserRole,
  auditProducts, auditTotal, auditPage, auditPageSize,
  loadAuditProducts, auditProduct,
  coupons, couponTotal, couponFilterActive, couponPage, couponPageSize,
  couponVisible, editingCoupon, couponSaving, couponForm,
  loadCoupons, openCouponEdit, saveCoupon, toggleCoupon,
  aiData, aiForecastOption, loadAIAnalysis,
  marketingSubTab, campaigns, campaignTotal, campaignFilterActive, campaignPage, campaignPageSize,
  campaignVisible, editingCampaign, campaignSaving, campaignForm,
  banners, bannerVisible, editingBanner, bannerSaving, bannerForm,
  loadCampaigns, openCampaignEdit, saveCampaign, toggleCampaign,
  loadBanners, openBannerEdit, saveBanner, deleteBanner,
  settingsForm, settingsSaving, loadSettings, saveSettings,
} = useAdmin()

onMounted(() => {
  loadStats(); loadProducts(); loadCategories(); loadOrders(); loadUsers(); loadAuditProducts(); loadCoupons(); loadAIAnalysis(); loadCampaigns(); loadBanners(); loadSettings()
})
</script>

<style scoped>
.admin-page { padding: 40px 0 60px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card { display: flex; align-items: center; gap: 12px; padding: 20px; }
.sc-icon { font-size: 32px; } .sc-value { font-size: 22px; font-weight: 700; display: block; } .sc-label { font-size: 12px; color: var(--text-light); }
.alert-bar { margin-bottom: 16px; }
.admin-tabs { margin-top: 8px; }
.charts-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.chart-card { padding: 20px; } .chart-card h3 { font-size: 14px; margin-bottom: 12px; } .chart { height: 280px; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.card-header h3 { font-size: 14px; }
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.batch-bar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f5f7fa; border-radius: 6px; margin-bottom: 12px; font-size: 13px; }
.pagination-bar { display: flex; justify-content: flex-end; margin-top: 16px; }
.text-danger { color: #e74c3c; font-weight: 600; }
.order-item-line { font-size: 13px; color: #606266; line-height: 1.6; }
.img-upload-wrap { display: flex; flex-direction: column; align-items: flex-start; }
.preview-img { width: 120px; height: 120px; object-fit: cover; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 8px; }
.img-placeholder { width: 120px; height: 120px; border-radius: 8px; border: 2px dashed #ccc; display: flex; align-items: center; justify-content: center; color: #999; font-size: 13px; margin-bottom: 8px; }
@media (max-width: 768px) {
  .stats-row, .charts-row { grid-template-columns: 1fr; }
  .filter-bar { flex-direction: column; align-items: stretch; }
  .filter-bar .el-input, .filter-bar .el-select { width: 100% !important; }
  .card-header { flex-direction: column; align-items: stretch; }
}
</style>
