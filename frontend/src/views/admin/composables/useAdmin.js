import { ref, reactive } from 'vue'
import { adminAPI, productsAPI, uploadAPI } from '../../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export function useAdmin() {
  const activeTab = ref('overview')

  // ====== 统计看板 ======
  const statsCards = ref([
    { icon: '💰', label: '总销售额', value: '¥0' },
    { icon: '👥', label: '用户数', value: '0' },
    { icon: '📦', label: '订单数', value: '0' },
    { icon: '🛒', label: '商品数', value: '0' }
  ])
  const alerts = ref([])

  const salesOption = ref({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: [], boundaryGap: false },
    yAxis: { type: 'value' },
    series: [{ data: [], type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, itemStyle: { color: '#6C5CE7' } }]
  })

  const categoryOption = ref({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '50%'],
      label: { show: true }, emphasis: { label: { fontSize: 16, fontWeight: 'bold' } },
      data: []
    }]
  })

  async function loadStats() {
    try {
      const res = await adminAPI.getStats()
      const s = res.data
      statsCards.value = [
        { icon: '💰', label: '总销售额', value: '¥' + (s.total_revenue || 0).toFixed(2) },
        { icon: '👥', label: '用户数', value: String(s.total_users || 0) },
        { icon: '📦', label: '订单数', value: String(s.total_orders || 0) },
        { icon: '🛒', label: '商品数', value: String(s.total_products || 0) }
      ]
      if (s.sales_trend) {
        salesOption.value.xAxis.data = s.sales_trend.map(i => i.date || '')
        salesOption.value.series[0].data = s.sales_trend.map(i => i.sales || 0)
      }
      if (s.category_dist) {
        categoryOption.value.series[0].data = s.category_dist.map(i => ({ name: i.category, value: i.count }))
      }
      alerts.value = []
      if (s.pending_audit > 0) {
        alerts.value.push({ type: 'warning', message: `有 ${s.pending_audit} 件商品待审核，请前往「商品审核」处理` })
      }
      if (s.low_stock > 0) {
        alerts.value.push({ type: 'error', message: `有 ${s.low_stock} 件商品库存低于 10，请前往「商品管理」查看` })
      }
    } catch (e) {
      console.error('Stats load failed:', e)
    }
  }

  // ====== 商品管理 ======
  const products = ref([])
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const filterKeyword = ref('')
  const filterStatus = ref('')
  const filterAudit = ref('')
  const selectedProductIds = ref([])

  const categories = ref([])
  const editVisible = ref(false)
  const editingProduct = ref(null)
  const saving = ref(false)
  const uploading = ref(false)
  const editForm = reactive({
    name: '', description: '', price: 0, original_price: null,
    stock: 0, image: '', category_id: null,
    brand: '', tags: [], is_active: true,
    is_recommend: false, is_new: false, is_sale: false
  })

  async function loadProducts() {
    try {
      const params = { page: page.value, page_size: pageSize.value }
      if (filterKeyword.value) params.keyword = filterKeyword.value
      if (filterStatus.value) params.status = filterStatus.value
      if (filterAudit.value) params.audit_status = filterAudit.value
      const res = await adminAPI.getProducts(params)
      const data = res.data
      products.value = data.items || []
      total.value = data.total || 0
    } catch (e) {
      console.error('Products load failed:', e)
    }
  }

  async function loadCategories() {
    try {
      const res = await productsAPI.getCategories()
      categories.value = res.data || []
    } catch (e) {
      console.error('Categories load failed:', e)
    }
  }

  function openEdit(product) {
    editingProduct.value = product
    if (product) {
      Object.assign(editForm, {
        name: product.name || '', description: product.description || '',
        price: product.price || 0, original_price: product.original_price || null,
        stock: product.stock || 0, image: product.image || '',
        category_id: product.category_id || null, brand: product.brand || '',
        tags: product.tags || [], is_active: product.is_active !== false,
        is_recommend: product.is_recommend || false,
        is_new: product.is_new || false, is_sale: product.is_sale || false,
      })
    } else {
      Object.assign(editForm, {
        name: '', description: '', price: 0, original_price: null,
        stock: 0, image: '', category_id: null, brand: '', tags: [],
        is_active: true, is_recommend: false, is_new: false, is_sale: false
      })
    }
    editVisible.value = true
  }

  async function customUpload(options) {
    uploading.value = true
    try {
      const res = await uploadAPI.uploadImage(options.file)
      editForm.image = res.data.url
      ElMessage.success('上传成功')
      options.onSuccess(res.data)
    } catch (e) {
      ElMessage.error('上传失败')
      options.onError(e)
    } finally {
      uploading.value = false
    }
  }

  async function saveProduct() {
    if (!editForm.name || editForm.price <= 0) {
      ElMessage.warning('请填写商品名称和售价')
      return
    }
    saving.value = true
    try {
      const payload = { ...editForm }
      if (editingProduct.value?.id) {
        await adminAPI.updateProduct(editingProduct.value.id, payload)
        ElMessage.success('更新成功')
      } else {
        await adminAPI.createProduct(payload)
        ElMessage.success('添加成功')
      }
      editVisible.value = false
      loadProducts()
      loadStats()
    } catch (e) {
      console.error(e)
    } finally {
      saving.value = false
    }
  }

  async function deleteProduct(id) {
    try {
      await ElMessageBox.confirm('确定下架该商品？', '提示', { type: 'warning' })
      await adminAPI.deleteProduct(id)
      ElMessage.success('已下架')
      loadProducts()
      loadStats()
    } catch {}
  }

  function handleSelectionChange(selection) {
    selectedProductIds.value = selection.map(r => r.id)
  }

  async function batchAction(action) {
    if (!selectedProductIds.value.length) return
    try {
      const msg = action === 'delete' ? '确定批量删除所选商品？' : `确定批量${action === 'activate' ? '上架' : '下架'}所选商品？`
      await ElMessageBox.confirm(msg, '提示', { type: 'warning' })
      await adminAPI.batchProducts({ ids: selectedProductIds.value, action })
      ElMessage.success('批量操作成功')
      selectedProductIds.value = []
      loadProducts()
      loadStats()
    } catch {}
  }

  async function showLowStock() {
    filterAudit.value = ''
    filterStatus.value = ''
    filterKeyword.value = ''
    try {
      const res = await adminAPI.getLowStock({ page: 1, page_size: 50 })
      products.value = res.data.items || []
      total.value = res.data.total || 0
      ElMessage.info(`显示库存预警商品共 ${total.value} 件`)
    } catch (e) {
      console.error(e)
    }
  }

  // ====== 订单管理 ======
  const orders = ref([])
  const orderPage = ref(1)
  const orderPageSize = ref(20)
  const orderTotal = ref(0)
  const orderStatusFilter = ref('')

  const shipVisible = ref(false)
  const shipLoading = ref(false)
  const shipForm = reactive({ order_id: null, logistics_company: '', tracking_no: '' })

  const orderStatusVisible = ref(false)
  const orderStatusLoading = ref(false)
  const orderStatusForm = reactive({ order_id: null, status: '' })

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

  async function loadOrders() {
    try {
      const params = { page: orderPage.value, page_size: orderPageSize.value }
      if (orderStatusFilter.value) params.status = orderStatusFilter.value
      const res = await adminAPI.getOrders(params)
      const data = res.data
      orders.value = data.items || []
      orderTotal.value = data.total || 0
    } catch (e) {
      console.error('Orders load failed:', e)
    }
  }

  function openShip(row) {
    shipForm.order_id = row.id
    shipForm.logistics_company = ''
    shipForm.tracking_no = ''
    shipVisible.value = true
  }

  async function confirmShip() {
    if (!shipForm.tracking_no) {
      ElMessage.warning('请输入物流单号')
      return
    }
    shipLoading.value = true
    try {
      await adminAPI.updateOrder(shipForm.order_id, {
        status: 'shipped',
        logistics_company: shipForm.logistics_company,
        tracking_no: shipForm.tracking_no,
      })
      ElMessage.success('发货成功')
      shipVisible.value = false
      loadOrders()
      loadStats()
    } catch (e) {
      console.error(e)
    } finally {
      shipLoading.value = false
    }
  }

  function openOrderStatus(row) {
    orderStatusForm.order_id = row.id
    orderStatusForm.status = row.status
    orderStatusVisible.value = true
  }

  async function confirmOrderStatus() {
    orderStatusLoading.value = true
    try {
      await adminAPI.updateOrder(orderStatusForm.order_id, {
        status: orderStatusForm.status,
      })
      ElMessage.success('状态更新成功')
      orderStatusVisible.value = false
      loadOrders()
      loadStats()
    } catch (e) {
      console.error(e)
    } finally {
      orderStatusLoading.value = false
    }
  }

  // ====== 用户管理 ======
  const users = ref([])
  const userPage = ref(1)
  const userPageSize = ref(20)
  const userTotal = ref(0)
  const userRoleFilter = ref('')

  async function loadUsers() {
    try {
      const params = { page: userPage.value, page_size: userPageSize.value }
      if (userRoleFilter.value) params.role = userRoleFilter.value
      const res = await adminAPI.getUsers(params)
      const data = res.data
      users.value = data.items || []
      userTotal.value = data.total || 0
    } catch (e) {
      console.error('Users load failed:', e)
    }
  }

  async function toggleUser(id) {
    try {
      const res = await adminAPI.toggleUserStatus(id)
      ElMessage.success(res.data.message)
      loadUsers()
      loadStats()
    } catch (e) {
      console.error(e)
    }
  }

  async function changeUserRole(id, role) {
    try {
      await adminAPI.updateUserRole(id, role)
      ElMessage.success('角色更新成功')
      loadUsers()
    } catch (e) {
      console.error(e)
    }
  }

  // ====== 商品审核 ======
  const auditProducts = ref([])
  const auditPage = ref(1)
  const auditPageSize = ref(20)
  const auditTotal = ref(0)

  async function loadAuditProducts() {
    try {
      const params = { page: auditPage.value, page_size: auditPageSize.value, audit_status: 'pending' }
      const res = await adminAPI.getProducts(params)
      const data = res.data
      auditProducts.value = data.items || []
      auditTotal.value = data.total || 0
    } catch (e) {
      console.error('Audit load failed:', e)
    }
  }

  async function auditProduct(id, status) {
    try {
      await adminAPI.auditProduct(id, { audit_status: status })
      ElMessage.success(status === 'approved' ? '已通过审核' : '已拒绝')
      loadAuditProducts()
      loadStats()
    } catch (e) {
      console.error(e)
    }
  }

  // ====== 优惠券 ======
  const coupons = ref([])
  const couponPage = ref(1)
  const couponPageSize = ref(20)
  const couponTotal = ref(0)
  const couponFilterActive = ref('')

  const couponVisible = ref(false)
  const editingCoupon = ref(null)
  const couponSaving = ref(false)
  const couponForm = reactive({
    code: '', name: '', description: '', discount_type: 'fixed',
    discount_value: 10, min_order_amount: 0, max_discount: null,
    valid_from: null, valid_until: null, total_limit: 0, per_user_limit: 1,
  })

  async function loadCoupons() {
    try {
      const params = { page: couponPage.value, page_size: couponPageSize.value }
      if (couponFilterActive.value !== '' && couponFilterActive.value !== null && couponFilterActive.value !== undefined) {
        params.is_active = couponFilterActive.value
      }
      const res = await adminAPI.getCoupons(params)
      const data = res.data
      coupons.value = data.items || []
      couponTotal.value = data.total || 0
    } catch (e) {
      console.error('Coupons load failed:', e)
    }
  }

  function openCouponEdit(coupon) {
    editingCoupon.value = coupon
    if (coupon) {
      Object.assign(couponForm, {
        code: coupon.code, name: coupon.name, description: coupon.description || '',
        discount_type: coupon.discount_type || 'fixed',
        discount_value: coupon.discount_value || 0,
        min_order_amount: coupon.min_order_amount || 0,
        max_discount: coupon.max_discount || null,
        valid_from: coupon.valid_from ? coupon.valid_from.slice(0, 19) : null,
        valid_until: coupon.valid_until ? coupon.valid_until.slice(0, 19) : null,
        total_limit: coupon.total_limit || 0,
        per_user_limit: coupon.per_user_limit || 1,
      })
    } else {
      Object.assign(couponForm, {
        code: '', name: '', description: '', discount_type: 'fixed',
        discount_value: 10, min_order_amount: 0, max_discount: null,
        valid_from: null, valid_until: null, total_limit: 0, per_user_limit: 1,
      })
    }
    couponVisible.value = true
  }

  async function saveCoupon() {
    if (!couponForm.code || !couponForm.name) {
      ElMessage.warning('请填写优惠码和名称')
      return
    }
    couponSaving.value = true
    try {
      const payload = { ...couponForm }
      if (editingCoupon.value?.id) {
        await adminAPI.updateCoupon(editingCoupon.value.id, payload)
        ElMessage.success('更新成功')
      } else {
        await adminAPI.createCoupon(payload)
        ElMessage.success('创建成功')
      }
      couponVisible.value = false
      loadCoupons()
    } catch (e) {
      console.error(e)
    } finally {
      couponSaving.value = false
    }
  }

  async function toggleCoupon(id) {
    try {
      const res = await adminAPI.toggleCoupon(id)
      ElMessage.success(res.data.message)
      loadCoupons()
    } catch (e) {
      console.error(e)
    }
  }

  // ====== AI 分析 ======
  const aiData = ref({
    sales_forecast: { historical: [], forecast: [], labels: [] },
    user_profile: { total_users: 0, new_users_7d: 0, old_users: 0, repurchase_rate: 0 },
    product_insights: { stagnant: [], potential: [] },
    suggestions: [],
  })

  const aiForecastOption = ref({
    tooltip: { trigger: 'axis' },
    legend: { data: ['历史销售', '预测销售'] },
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value' },
    series: [
      { name: '历史销售', type: 'line', data: [], smooth: true, itemStyle: { color: '#6C5CE7' } },
      { name: '预测销售', type: 'line', data: [], smooth: true, lineStyle: { type: 'dashed' }, itemStyle: { color: '#e74c3c' } },
    ]
  })

  async function loadAIAnalysis() {
    try {
      const res = await adminAPI.getAIAnalysis()
      const d = res.data
      aiData.value = d
      if (d.sales_forecast) {
        const histLen = d.sales_forecast.historical.length
        const allData = [...d.sales_forecast.historical, ...d.sales_forecast.forecast]
        const histData = d.sales_forecast.historical.concat(new Array(d.sales_forecast.forecast.length).fill(null))
        const forecastData = new Array(histLen - 1).fill(null).concat([d.sales_forecast.historical[histLen - 1], ...d.sales_forecast.forecast])
        aiForecastOption.value.xAxis.data = d.sales_forecast.labels
        aiForecastOption.value.series[0].data = histData
        aiForecastOption.value.series[1].data = forecastData
      }
    } catch (e) {
      console.error('AI analysis load failed:', e)
    }
  }

  // ====== 营销管理 ======
  const marketingSubTab = ref('campaigns')
  const campaigns = ref([])
  const campaignPage = ref(1)
  const campaignPageSize = ref(20)
  const campaignTotal = ref(0)
  const campaignFilterActive = ref('')

  const campaignVisible = ref(false)
  const editingCampaign = ref(null)
  const campaignSaving = ref(false)
  const campaignForm = reactive({
    name: '', campaign_type: 'discount', description: '', banner_image: '',
    discount_value: 10, min_order_amount: 0,
    start_time: null, end_time: null,
  })

  const banners = ref([])
  const bannerVisible = ref(false)
  const editingBanner = ref(null)
  const bannerSaving = ref(false)
  const bannerForm = reactive({ title: '', image: '', link: '', sort_order: 0 })

  function campaignTypeLabel(type) {
    const map = { discount: '固定减免', flash_sale: '限时折扣', full_reduction: '满减' }
    return map[type] || type
  }

  function formatDate(d) {
    if (!d) return '-'
    return d.slice(0, 16).replace('T', ' ')
  }

  async function loadCampaigns() {
    try {
      const params = { page: campaignPage.value, page_size: campaignPageSize.value }
      if (campaignFilterActive.value !== '' && campaignFilterActive.value !== null && campaignFilterActive.value !== undefined) {
        params.is_active = campaignFilterActive.value
      }
      const res = await adminAPI.getCampaigns(params)
      const data = res.data
      campaigns.value = data.items || []
      campaignTotal.value = data.total || 0
    } catch (e) {
      console.error('Campaigns load failed:', e)
    }
  }

  function openCampaignEdit(campaign) {
    editingCampaign.value = campaign
    if (campaign) {
      Object.assign(campaignForm, {
        name: campaign.name, campaign_type: campaign.campaign_type || 'discount',
        description: campaign.description || '', banner_image: campaign.banner_image || '',
        discount_value: campaign.discount_value || 0, min_order_amount: campaign.min_order_amount || 0,
        start_time: campaign.start_time ? campaign.start_time.slice(0, 19) : null,
        end_time: campaign.end_time ? campaign.end_time.slice(0, 19) : null,
      })
    } else {
      Object.assign(campaignForm, {
        name: '', campaign_type: 'discount', description: '', banner_image: '',
        discount_value: 10, min_order_amount: 0, start_time: null, end_time: null,
      })
    }
    campaignVisible.value = true
  }

  async function saveCampaign() {
    if (!campaignForm.name) {
      ElMessage.warning('请填写活动名称')
      return
    }
    campaignSaving.value = true
    try {
      const payload = { ...campaignForm }
      if (editingCampaign.value?.id) {
        await adminAPI.updateCampaign(editingCampaign.value.id, payload)
        ElMessage.success('更新成功')
      } else {
        await adminAPI.createCampaign(payload)
        ElMessage.success('创建成功')
      }
      campaignVisible.value = false
      loadCampaigns()
    } catch (e) {
      console.error(e)
    } finally {
      campaignSaving.value = false
    }
  }

  async function toggleCampaign(id) {
    try {
      const res = await adminAPI.toggleCampaign(id)
      ElMessage.success(res.data.message)
      loadCampaigns()
    } catch (e) {
      console.error(e)
    }
  }

  async function loadBanners() {
    try {
      const res = await adminAPI.getBanners()
      banners.value = res.data || []
    } catch (e) {
      console.error('Banners load failed:', e)
    }
  }

  function openBannerEdit(banner) {
    editingBanner.value = banner
    if (banner) {
      Object.assign(bannerForm, {
        title: banner.title, image: banner.image, link: banner.link, sort_order: banner.sort_order || 0,
      })
    } else {
      Object.assign(bannerForm, { title: '', image: '', link: '', sort_order: 0 })
    }
    bannerVisible.value = true
  }

  async function saveBanner() {
    if (!bannerForm.image) {
      ElMessage.warning('请填写图片URL')
      return
    }
    bannerSaving.value = true
    try {
      const payload = { ...bannerForm }
      if (editingBanner.value?.id) {
        await adminAPI.updateBanner(editingBanner.value.id, payload)
        ElMessage.success('更新成功')
      } else {
        await adminAPI.createBanner(payload)
        ElMessage.success('创建成功')
      }
      bannerVisible.value = false
      loadBanners()
    } catch (e) {
      console.error(e)
    } finally {
      bannerSaving.value = false
    }
  }

  async function deleteBanner(id) {
    try {
      await ElMessageBox.confirm('确定删除该Banner？', '提示', { type: 'warning' })
      await adminAPI.deleteBanner(id)
      ElMessage.success('已删除')
      loadBanners()
    } catch {}
  }

  // ====== 系统设置 ======
  const settingsForm = reactive({
    site_name: '', site_logo: '', service_phone: '', service_email: '',
    pay_wechat: true, pay_alipay: true, pay_cod: false,
    shipping_fee: 10, free_shipping_threshold: 99,
    notify_order: true, notify_register: true, notify_low_stock: true,
  })
  const settingsSaving = ref(false)

  async function loadSettings() {
    try {
      const res = await adminAPI.getConfigs()
      const configs = res.data || {}
      const getVal = (key, def) => configs[key]?.value || def
      const getBool = (key, def) => {
        const v = getVal(key, String(def))
        return v === 'true' || v === '1' || v === true
      }
      Object.assign(settingsForm, {
        site_name: getVal('site_name', 'SmartMall AI'),
        site_logo: getVal('site_logo', ''),
        service_phone: getVal('service_phone', ''),
        service_email: getVal('service_email', ''),
        pay_wechat: getBool('pay_wechat', true),
        pay_alipay: getBool('pay_alipay', true),
        pay_cod: getBool('pay_cod', false),
        shipping_fee: parseFloat(getVal('shipping_fee', '10')) || 10,
        free_shipping_threshold: parseFloat(getVal('free_shipping_threshold', '99')) || 99,
        notify_order: getBool('notify_order', true),
        notify_register: getBool('notify_register', true),
        notify_low_stock: getBool('notify_low_stock', true),
      })
    } catch (e) {
      console.error('Settings load failed:', e)
    }
  }

  async function saveSettings() {
    settingsSaving.value = true
    try {
      const items = [
        { config_key: 'site_name', config_value: settingsForm.site_name, description: '网站名称' },
        { config_key: 'site_logo', config_value: settingsForm.site_logo, description: '网站Logo' },
        { config_key: 'service_phone', config_value: settingsForm.service_phone, description: '客服电话' },
        { config_key: 'service_email', config_value: settingsForm.service_email, description: '客服邮箱' },
        { config_key: 'pay_wechat', config_value: String(settingsForm.pay_wechat), description: '微信支付' },
        { config_key: 'pay_alipay', config_value: String(settingsForm.pay_alipay), description: '支付宝' },
        { config_key: 'pay_cod', config_value: String(settingsForm.pay_cod), description: '货到付款' },
        { config_key: 'shipping_fee', config_value: String(settingsForm.shipping_fee), description: '默认运费' },
        { config_key: 'free_shipping_threshold', config_value: String(settingsForm.free_shipping_threshold), description: '包邮门槛' },
        { config_key: 'notify_order', config_value: String(settingsForm.notify_order), description: '订单通知' },
        { config_key: 'notify_register', config_value: String(settingsForm.notify_register), description: '注册通知' },
        { config_key: 'notify_low_stock', config_value: String(settingsForm.notify_low_stock), description: '低库存提醒' },
      ]
      await adminAPI.updateConfigs(items)
      ElMessage.success('设置已保存')
    } catch (e) {
      console.error(e)
    } finally {
      settingsSaving.value = false
    }
  }

  return {
    activeTab,
    statsCards, alerts, salesOption, categoryOption, loadStats,
    products, page, pageSize, total, filterKeyword, filterStatus, filterAudit, selectedProductIds,
    categories, editVisible, editingProduct, saving, uploading, editForm,
    loadProducts, loadCategories, openEdit, customUpload, saveProduct, deleteProduct,
    handleSelectionChange, batchAction, showLowStock,
    orders, orderPage, orderPageSize, orderTotal, orderStatusFilter,
    shipVisible, shipLoading, shipForm,
    orderStatusVisible, orderStatusLoading, orderStatusForm,
    orderStatusLabel, orderStatusType,
    loadOrders, openShip, confirmShip, openOrderStatus, confirmOrderStatus,
    users, userPage, userPageSize, userTotal, userRoleFilter,
    loadUsers, toggleUser, changeUserRole,
    auditProducts, auditPage, auditPageSize, auditTotal,
    loadAuditProducts, auditProduct,
    coupons, couponPage, couponPageSize, couponTotal, couponFilterActive,
    couponVisible, editingCoupon, couponSaving, couponForm,
    loadCoupons, openCouponEdit, saveCoupon, toggleCoupon,
    aiData, aiForecastOption, loadAIAnalysis,
    marketingSubTab, campaigns, campaignPage, campaignPageSize, campaignTotal, campaignFilterActive,
    campaignVisible, editingCampaign, campaignSaving, campaignForm,
    banners, bannerVisible, editingBanner, bannerSaving, bannerForm,
    campaignTypeLabel, formatDate,
    loadCampaigns, openCampaignEdit, saveCampaign, toggleCampaign,
    loadBanners, openBannerEdit, saveBanner, deleteBanner,
    settingsForm, settingsSaving, loadSettings, saveSettings,
  }
}
